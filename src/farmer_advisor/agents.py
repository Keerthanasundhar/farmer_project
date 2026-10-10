from __future__ import annotations

import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .config import TAVILY_API_KEY
from .knowledge import CROP_ALIASES, get_crop_guidance
from .weather import build_weather_summary, fetch_forecast, weather_code_to_label


class AdvisorState(TypedDict):
    question: str
    crop: str | None
    location: str | None
    forecast: dict | None
    alert_flags: list[str]
    soil_moisture: str
    crop_guidance: list[str]
    final_advice: str
    sources: list[str]


def extract_crop(question: str) -> str | None:
    text = question.lower()
    for crop, alias in CROP_ALIASES.items():
        if crop in text or alias in text:
            return crop
    return None


def extract_location(question: str) -> str | None:
    matches = re.findall(r"(?:near|in|for|at)\s+([A-Z][a-zA-Z\s-]+)", question)
    if matches:
        location = matches[0].strip()
        if location:
            return location
    return None


def get_soil_moisture(location: str, crop: str) -> str:
    crop_key = (crop or "generic").lower()
    moisture_map = {
        "paddy": "High moisture (the field is likely damp and irrigation should be managed to avoid waterlogging)",
        "cotton": "Moderate moisture (check the root zone for stress before deciding on irrigation)",
        "banana": "High moisture with drainage checks needed before a storm or heavy rainfall window",
        "groundnut": "Moderate moisture; watch the pegging stage and avoid waterlogging after rain",
    }
    return moisture_map.get(crop_key, "Moderate moisture; verify conditions for the crop and location")


def detect_alerts(forecast: dict | None) -> list[str]:
    if not forecast:
        return []
    alerts = []
    for day in forecast.get("summary", [])[:3]:
        if day.get("rain_probability_pct", 0) > 70:
            alerts.append(f"Heavy rain risk on {day['date']} with {day['rain_probability_pct']}% precipitation probability")
        if day.get("weather_code") in {61, 63, 65, 80, 81, 82, 95}:
            alerts.append(f"Severe weather risk on {day['date']}: {weather_code_to_label(day.get('weather_code'))}")
    return alerts


def tavily_search(query: str) -> list[str]:
    api_key = TAVILY_API_KEY
    if not api_key:
        return ["Tavily API key not configured; using local weather and agronomy guidance fallback."]
    try:
        import requests

        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "max_results": 3},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        results = []
        for item in payload.get("results", [])[:3]:
            results.append(item.get("title", "Local alert") + ": " + item.get("content", "No summary available."))
        return results or ["No active alerts retrieved from Tavily."]
    except Exception:
        return ["Alert service unavailable; using forecast-based advisory and local agronomy guidance."]


def supervisor_node(state: AdvisorState) -> AdvisorState:
    question = state["question"]
    crop = extract_crop(question) or state.get("crop")
    location = extract_location(question) or state.get("location")

    if not crop or not location:
        state["final_advice"] = (
            "Please share the crop and location. For example: 'I grow paddy near Thanjavur. Should I irrigate this week?'"
        )
        state["sources"] = ["System guardrail: ask for missing crop and location"]
        return state

    state["crop"] = crop
    state["location"] = location
    return state


def forecast_agent_node(state: AdvisorState) -> AdvisorState:
    forecast = fetch_forecast(state["location"])
    state["forecast"] = forecast
    state["alert_flags"] = detect_alerts(forecast)
    state["sources"] = [forecast.get("api_source", "Open-Meteo")]
    return state


def soil_tool_node(state: AdvisorState) -> AdvisorState:
    state["soil_moisture"] = get_soil_moisture(state["location"], state["crop"])
    return state


def alert_agent_node(state: AdvisorState) -> AdvisorState:
    forecast = state.get("forecast")
    if not forecast:
        state["alert_flags"] = []
        return state

    alert_result = detect_alerts(forecast)
    if alert_result:
        web_alerts = tavily_search(f"current weather alerts for {state['location']} and {state['crop']} crop")
        state["alert_flags"] = alert_result + web_alerts
    else:
        state["alert_flags"] = ["No active severe weather alert detected in the local forecast."]
    state["sources"].append("Tavily / local alert review")
    return state


def crop_advisor_agent_node(state: AdvisorState) -> AdvisorState:
    forecast = state.get("forecast")
    crop = state["crop"]
    summary = build_weather_summary(forecast) if forecast else "forecast not available"
    guidance = get_crop_guidance(crop, summary)

    actions = []
    if any("rain" in alert.lower() or "storm" in alert.lower() for alert in state.get("alert_flags", [])):
        actions.append("Avoid spraying pesticides immediately before heavy rain; prefer a break in rainfall and apply in a dry window.")
    else:
        actions.append("Use the next 48-72 hours to plan irrigation and monitor the crop canopy for moisture stress.")

    if crop == "paddy":
        actions.append("Keep field water levels steady and maintain drainage to avoid ponding during rainfall.")
    elif crop == "cotton":
        actions.append("Check boll development and protect against moisture stress in warm, dry intervals.")
    elif crop == "banana":
        actions.append("Protect the plantation from strong winds and improve drainage before the storm peak.")
    elif crop == "groundnut":
        actions.append("Prioritize pod maturity and plan harvest during a dry spell to reduce fungal risk.")

    state["crop_guidance"] = guidance + actions
    state["sources"].append("TNAU agronomy guidance")
    return state


def report_writer_node(state: AdvisorState) -> AdvisorState:
    crop = state["crop"]
    location = state["location"]
    forecast = state["forecast"] or {"summary": []}
    weather_text = build_weather_summary(forecast)
    soil_info = state.get("soil_moisture", "Moderate soil moisture")
    alert_lines = state.get("alert_flags", [])
    raw_guidance = [str(item).lstrip("- ").strip() for item in state.get("crop_guidance", [])]
    guidance = "\n".join(f"- {item}" for item in raw_guidance)

    advisory = (
        f"Farmer advisory for {crop.title()} in {location}:\n"
        f"Weather overview: {weather_text}.\n"
        f"Current soil condition: {soil_info}.\n"
        f"Alerts: {', '.join(alert_lines) if alert_lines else 'No major alert detected.'}\n"
        f"Action plan:\n{guidance}\n"
        "This advice is based on forecast patterns and accessible agronomy guidance; local field checks are still important."
    )

    state["final_advice"] = advisory
    state["sources"] = list(dict.fromkeys(state.get("sources", [])))
    return state


def route_after_supervisor(state: AdvisorState) -> str:
    if state.get("final_advice"):
        return "END"
    return "forecast_agent"


def build_graph() -> StateGraph:
    workflow = StateGraph(AdvisorState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("forecast_agent", forecast_agent_node)
    workflow.add_node("soil_tool", soil_tool_node)
    workflow.add_node("alert_agent", alert_agent_node)
    workflow.add_node("crop_advisor_agent", crop_advisor_agent_node)
    workflow.add_node("report_writer", report_writer_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "END": END,
            "forecast_agent": "forecast_agent",
        },
    )
    workflow.add_edge("forecast_agent", "soil_tool")
    workflow.add_conditional_edges(
        "soil_tool",
        lambda state: "alert_agent" if state.get("alert_flags") else "crop_advisor_agent",
        {
            "alert_agent": "alert_agent",
            "crop_advisor_agent": "crop_advisor_agent",
        },
    )
    workflow.add_edge("alert_agent", "crop_advisor_agent")
    workflow.add_edge("crop_advisor_agent", "report_writer")
    workflow.add_edge("report_writer", END)
    return workflow


class FarmerAdvisorGraph:
    def __init__(self) -> None:
        self.graph = build_graph().compile()

    def run(self, question: str) -> dict:
        initial_state: AdvisorState = {
            "question": question,
            "crop": None,
            "location": None,
            "forecast": None,
            "alert_flags": [],
            "soil_moisture": "Moderate moisture",
            "crop_guidance": [],
            "final_advice": "",
            "sources": [],
        }
        result = self.graph.invoke(initial_state)
        return {
            "crop": result.get("crop"),
            "location": result.get("location"),
            "final_advice": result.get("final_advice", "No advice generated."),
            "sources": result.get("sources", []),
        }
