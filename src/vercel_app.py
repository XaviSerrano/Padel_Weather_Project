import os

from src.config import WeatherThresholds
from src.extract.weather_extractor import OpenMeteoExtractor
from src.main import create_handler
from src.services.club_service import ClubService
from src.services.weather_service import WeatherService


def build_handler():
    thresholds = WeatherThresholds.from_environment()
    club_service = ClubService(os.getenv("GOOGLE_PLACES_API_KEY", "").strip())
    weather_service = WeatherService(OpenMeteoExtractor(), thresholds)
    return create_handler(club_service, weather_service)