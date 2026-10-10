from __future__ import annotations

from pathlib import Path

GUIDE_PATH = Path(__file__).resolve().parents[2] / "data" / "crop_guides.md"

CROP_ALIASES = {
    "paddy": "paddy",
    "rice": "paddy",
    "cotton": "cotton",
    "banana": "banana",
    "groundnut": "groundnut",
    "peanut": "groundnut",
}


def load_guides() -> str:
    return GUIDE_PATH.read_text(encoding="utf-8")


def get_crop_guidance(crop: str, forecast_summary: str) -> list[str]:
    normalized = (crop or "").strip().lower()
    crop_name = CROP_ALIASES.get(normalized, normalized or "generic")
    text = load_guides()
    if crop_name == "generic":
        return [
            "Use local agronomy guidance and ask for crop and location if missing.",
            "Prioritize irrigation and spray timing based on the coming forecast window.",
            "Keep an eye on active weather warnings and local market conditions before harvest.",
        ]

    lines = []
    current_section = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## "):
            current_section = stripped[3:].strip().lower()
            continue
        if current_section == crop_name:
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    if not lines:
        lines.append("Use local agronomy guidance for careful crop management during the forecast window.")
    if forecast_summary:
        lines.append(f"Forecast context: {forecast_summary}")
    return lines[:5]
