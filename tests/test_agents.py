import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from farmer_advisor.agents import FarmerAdvisorGraph


class FarmerAdvisorGraphTests(unittest.TestCase):
    @patch("farmer_advisor.agents.fetch_forecast")
    def test_missing_crop_or_location_returns_prompt_without_fetching_forecast(self, fetch_forecast):
        advisor = FarmerAdvisorGraph()

        for question in ("Should I irrigate this week?", "I grow paddy. Should I irrigate?"):
            with self.subTest(question=question):
                result = advisor.run(question)
                self.assertIn("Please share the crop and location", result["final_advice"])

        fetch_forecast.assert_not_called()

    @patch("farmer_advisor.agents.fetch_forecast")
    def test_complete_question_continues_to_generate_advice(self, fetch_forecast):
        fetch_forecast.return_value = {
            "location": "Thanjavur",
            "country": "India",
            "summary": [
                {
                    "date": "Today",
                    "max_temp_c": 31,
                    "min_temp_c": 25,
                    "rain_probability_pct": 10,
                    "total_precip_mm": 0,
                    "weather_code": 0,
                }
            ],
            "alert_level": "low",
            "api_source": "Open-Meteo",
        }
        advisor = FarmerAdvisorGraph()

        result = advisor.run("I grow paddy near Thanjavur. Should I irrigate this week?")

        self.assertIn("Farmer advisory for Paddy in Thanjavur", result["final_advice"])
        fetch_forecast.assert_called_once_with("Thanjavur")


if __name__ == "__main__":
    unittest.main()
