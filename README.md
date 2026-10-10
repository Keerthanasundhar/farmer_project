# Farmer Crop & Weather Advisor

This project implements a multi-agent agricultural advisor that combines weather forecasting, local agronomy guidance, and alert review for small and marginal farmers.

## Objective
Build a multi-agent advisor that helps farmers interpret live weather conditions and crop-specific agricultural guidance for the upcoming days.

## Included features
- Live weather forecast lookup via Open-Meteo (with a local fallback if the service is unavailable)
- Soil moisture estimation tool for crop and location planning
- RAG-style crop guidance from local agronomy notes
- Alert review process for heavy rain, cyclone, and market disruption signals
- LangGraph-style workflow with supervisor, forecasting, alert, crop advisor, and report writer nodes
- Streamlit UI for easy local interaction

## Example user queries
- I grow paddy near Thanjavur. Should I irrigate this week?
- Is it safe to spray pesticide on my cotton crop tomorrow?
- There is a cyclone warning. What should I do to protect my banana plantation?
- What is the best time to harvest groundnut given this week's forecast?

## Run locally
1. Open a terminal in the project root.
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   streamlit run app.py
   ```
4. Enter the crop and location details in the form and click Get advice.

## Key design notes
- The workflow conditionally sends the advisory to the alert agent when severe weather risk is detected.
- The system asks for missing crop and location data before producing a recommendation.
- It uses plain language recommendations and cites the forecast and agronomy sources used.
