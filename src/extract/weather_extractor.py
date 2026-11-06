import math
from urllib.parse import urlencode
from urllib.request import Request

from src.errors import ExternalServiceError
from src.extract.http_json import request_json


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = (
    "temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m"
)


class OpenMeteoExtractor:
    def __init__(self, timeout: float = 10):
        self.timeout = timeout

    def fetch(self, latitude: float, longitude: float):
        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise ValueError("Las coordenadas del club no son válidas.")

        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": HOURLY_VARIABLES,
                "timezone": "auto",
                "forecast_days": 7,
            }
        )
        request = Request(f"{OPEN_METEO_FORECAST_URL}?{query}")
        return request_json(request, "Open-Meteo", timeout=self.timeout)
