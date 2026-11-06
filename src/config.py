import math
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherThresholds:
    moderate_wind_kmh: float = 15
    high_wind_kmh: float = 25
    rain_probability_percent: float = 40
    min_temperature_c: float = 10
    max_temperature_c: float = 32

    @classmethod
    def from_environment(cls):
        thresholds = cls(
            moderate_wind_kmh=float(os.getenv("PADEL_MODERATE_WIND_KMH", "15")),
            high_wind_kmh=float(os.getenv("PADEL_HIGH_WIND_KMH", "25")),
            rain_probability_percent=float(os.getenv("PADEL_RAIN_PROBABILITY_PERCENT", "40")),
            min_temperature_c=float(os.getenv("PADEL_MIN_TEMP_C", "10")),
            max_temperature_c=float(os.getenv("PADEL_MAX_TEMP_C", "32")),
        )
        values = (
            thresholds.moderate_wind_kmh,
            thresholds.high_wind_kmh,
            thresholds.rain_probability_percent,
            thresholds.min_temperature_c,
            thresholds.max_temperature_c,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Los umbrales meteorológicos deben ser números finitos.")
        if thresholds.moderate_wind_kmh >= thresholds.high_wind_kmh:
            raise ValueError("El umbral de viento moderado debe ser menor que el de viento fuerte.")
        if not 0 <= thresholds.rain_probability_percent <= 100:
            raise ValueError("El umbral de lluvia debe estar entre 0 y 100.")
        if thresholds.min_temperature_c >= thresholds.max_temperature_c:
            raise ValueError("La temperatura mínima debe ser menor que la máxima.")
        return thresholds
