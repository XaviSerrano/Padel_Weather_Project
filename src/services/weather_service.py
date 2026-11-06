import math
from datetime import datetime

from src.config import WeatherThresholds
from src.errors import ExternalServiceError


class WeatherService:
    def __init__(self, extractor, thresholds: WeatherThresholds):
        self.extractor = extractor
        self.thresholds = thresholds

    def for_date(self, latitude: float, longitude: float, selected_date: str, court_type: str):
        if court_type not in {"indoor", "outdoor"}:
            raise ValueError("El tipo de pista debe ser indoor u outdoor.")
        try:
            datetime.strptime(selected_date, "%Y-%m-%d")
        except (TypeError, ValueError) as error:
            raise ValueError("La fecha debe tener el formato AAAA-MM-DD.") from error

        payload = self.extractor.fetch(latitude, longitude)
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise ExternalServiceError("Open-Meteo no devolvió previsiones horarias.")

        fields = {
            "time": hourly.get("time"),
            "temperature": hourly.get("temperature_2m"),
            "precipitation_probability": hourly.get("precipitation_probability"),
            "wind_speed": hourly.get("wind_speed_10m"),
            "wind_gusts": hourly.get("wind_gusts_10m"),
        }
        if any(not isinstance(values, list) for values in fields.values()):
            raise ExternalServiceError("Open-Meteo devolvió datos horarios incompletos.")

        forecasts = []
        for index, timestamp in enumerate(fields["time"]):
            if not isinstance(timestamp, str) or not timestamp.startswith(selected_date):
                continue
            try:
                local_time = datetime.fromisoformat(timestamp)
                temperature = _number(fields["temperature"][index])
                rain = _number(fields["precipitation_probability"][index])
                wind = _number(fields["wind_speed"][index])
                gusts = _number(fields["wind_gusts"][index])
            except (IndexError, TypeError, ValueError) as error:
                raise ExternalServiceError("Open-Meteo devolvió una hora incompleta o no válida.") from error

            forecast = {
                "time": local_time.strftime("%H:%M"),
                "temperature_c": temperature,
                "precipitation_probability_percent": rain,
                "wind_speed_kmh": wind,
                "wind_gusts_kmh": gusts,
            }
            forecast.update(self._rating(forecast, court_type))
            forecasts.append(forecast)

        if not forecasts:
            raise ValueError(
                "No hay previsión disponible para esa fecha. Elige un día dentro de los próximos 7."
            )
        forecasts.sort(key=lambda forecast: (-forecast["score"], forecast["time"]))
        return forecasts

    def _rating(self, forecast, court_type: str):
        if court_type == "indoor":
            return {
                "score": 100,
                "rating": "Indoor · sin penalización",
                "conditions": ["Sin penalización meteorológica"],
            }

        thresholds = self.thresholds
        penalties = []
        conditions = []
        rain = forecast["precipitation_probability_percent"]
        wind = forecast["wind_speed_kmh"]
        temperature = forecast["temperature_c"]

        if rain >= thresholds.rain_probability_percent:
            conditions.append("Posible lluvia")
            penalties.append(55)
        if wind >= thresholds.high_wind_kmh:
            conditions.append("Viento fuerte")
            penalties.append(40)
        elif wind >= thresholds.moderate_wind_kmh:
            conditions.append("Viento moderado")
            penalties.append(20)
        if temperature < thresholds.min_temperature_c:
            conditions.append("Temperatura baja")
            penalties.append(15)
        elif temperature > thresholds.max_temperature_c:
            conditions.append("Temperatura alta")
            penalties.append(15)

        if not conditions:
            conditions.append("Condiciones favorables")
        if rain >= thresholds.rain_probability_percent:
            rating = "Posible lluvia"
        elif wind >= thresholds.high_wind_kmh:
            rating = "Viento fuerte"
        elif wind >= thresholds.moderate_wind_kmh:
            rating = "Viento moderado"
        elif temperature < thresholds.min_temperature_c or temperature > thresholds.max_temperature_c:
            rating = "Temperatura poco cómoda"
        else:
            rating = "Favorable"
        return {
            "score": max(0, 100 - sum(penalties)),
            "rating": rating,
            "conditions": conditions,
        }


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("El valor debe ser un número finito.")
    return number
