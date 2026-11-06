import unittest

from src.config import WeatherThresholds
from src.services.weather_service import WeatherService


class FakeWeatherExtractor:
    def fetch(self, latitude, longitude):
        return {
            "hourly": {
                "time": ["2026-11-07T18:00", "2026-11-07T16:00", "2026-11-07T17:00"],
                "temperature_2m": [21, 20, 20],
                "precipitation_probability": [65, 5, 5],
                "wind_speed_10m": [8, 8, 18],
                "wind_gusts_10m": [12, 12, 25],
            }
        }


class WeatherServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = WeatherService(FakeWeatherExtractor(), WeatherThresholds())

    def test_outdoor_forecasts_are_ranked_by_weather_score(self):
        forecasts = self.service.for_date(41.39, 2.16, "2026-11-07", "outdoor")

        self.assertEqual([item["time"] for item in forecasts], ["16:00", "17:00", "18:00"])
        self.assertEqual(forecasts[0]["rating"], "Favorable")
        self.assertEqual(forecasts[1]["rating"], "Viento moderado")
        self.assertEqual(forecasts[2]["rating"], "Posible lluvia")

    def test_indoor_forecasts_are_not_penalized_by_weather(self):
        forecasts = self.service.for_date(41.39, 2.16, "2026-11-07", "indoor")

        self.assertTrue(all(item["score"] == 100 for item in forecasts))
        self.assertTrue(all(item["rating"] == "Indoor · sin penalización" for item in forecasts))
        self.assertEqual([item["time"] for item in forecasts], ["16:00", "17:00", "18:00"])

    def test_date_without_forecast_is_reported(self):
        with self.assertRaisesRegex(ValueError, "No hay previsión"):
            self.service.for_date(41.39, 2.16, "2026-11-08", "outdoor")

    def test_court_type_is_validated(self):
        with self.assertRaisesRegex(ValueError, "indoor u outdoor"):
            self.service.for_date(41.39, 2.16, "2026-11-07", "covered")


if __name__ == "__main__":
    unittest.main()
