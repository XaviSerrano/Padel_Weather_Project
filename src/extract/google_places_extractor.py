import json
import math
import re
from urllib.parse import quote, urlencode
from urllib.request import Request

from src.errors import ExternalServiceError
from src.extract.http_json import request_json


GOOGLE_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
GOOGLE_PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places"
GOOGLE_PLACES_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location"
)
GOOGLE_PLACES_AUTOCOMPLETE_FIELD_MASK = (
    "suggestions.placePrediction.placeId,"
    "suggestions.placePrediction.structuredFormat.mainText.text,"
    "suggestions.placePrediction.structuredFormat.secondaryText.text"
)
GOOGLE_PLACE_DETAILS_FIELD_MASK = "id,displayName,formattedAddress,location"


class GooglePlacesExtractor:
    def __init__(self, api_key: str, timeout: float = 10):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError("La búsqueda debe tener entre 1 y 200 caracteres.")

        request = Request(
            GOOGLE_PLACES_SEARCH_URL,
            data=json.dumps({"textQuery": query.strip()}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK,
            },
            method="POST",
        )
        payload = request_json(request, "Google Places", timeout=self.timeout)
        places = payload.get("places", [])
        if not isinstance(places, list):
            raise ExternalServiceError("Google Places devolvió una lista de clubes no válida.")
        return [self._normalize_place(place) for place in places]

    def autocomplete(self, query: str, session_token: str | None = None):
        if not isinstance(query, str) or not 3 <= len(query.strip()) <= 200:
            raise ValueError("Escribe entre 3 y 200 caracteres para ver sugerencias.")
        _validate_session_token(session_token)

        body: dict[str, str | list[str]] = {
            "input": query.strip(),
            "includedRegionCodes": ["es"],
            "languageCode": "es",
        }
        if session_token:
            body["sessionToken"] = session_token
        request = Request(
            GOOGLE_PLACES_AUTOCOMPLETE_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": GOOGLE_PLACES_AUTOCOMPLETE_FIELD_MASK,
            },
            method="POST",
        )
        payload = request_json(request, "Google Places Autocomplete", timeout=self.timeout)
        suggestions = payload.get("suggestions", [])
        if not isinstance(suggestions, list):
            raise ExternalServiceError(
                "Google Places Autocomplete devolvió sugerencias no válidas."
            )

        results = []
        for suggestion in suggestions:
            if not isinstance(suggestion, dict):
                raise ExternalServiceError(
                    "Google Places Autocomplete devolvió una sugerencia no válida."
                )
            prediction = suggestion.get("placePrediction")
            if prediction is None:
                continue
            if not isinstance(prediction, dict):
                raise ExternalServiceError(
                    "Google Places Autocomplete devolvió una sugerencia no válida."
                )
            structured_format = prediction.get("structuredFormat", {})
            main_text = (
                structured_format.get("mainText")
                if isinstance(structured_format, dict)
                else None
            )
            secondary_text = (
                structured_format.get("secondaryText")
                if isinstance(structured_format, dict)
                else None
            )
            full_text = prediction.get("text")
            place_id = prediction.get("placeId")
            name = main_text.get("text") if isinstance(main_text, dict) else None
            address = secondary_text.get("text") if isinstance(secondary_text, dict) else ""
            if not name and isinstance(full_text, dict):
                name = full_text.get("text")
            if not isinstance(place_id, str) or not place_id or not isinstance(name, str) or not name:
                raise ExternalServiceError(
                    "Google Places Autocomplete devolvió una sugerencia incompleta."
                )
            if not isinstance(address, str):
                raise ExternalServiceError(
                    "Google Places Autocomplete devolvió una sugerencia incompleta."
                )
            results.append({"place_id": place_id, "name": name, "address": address})
        return results

    def get_place(self, place_id: str, session_token: str | None = None):
        if not isinstance(place_id, str) or not place_id.strip() or len(place_id) > 512:
            raise ValueError("El identificador del club no es válido.")
        _validate_session_token(session_token)

        query = urlencode({"sessionToken": session_token}) if session_token else ""
        url = f"{GOOGLE_PLACES_DETAILS_URL}/{quote(place_id.strip(), safe='')}"
        if query:
            url = f"{url}?{query}"
        request = Request(
            url,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": GOOGLE_PLACE_DETAILS_FIELD_MASK,
            },
        )
        payload = request_json(request, "Google Places Details", timeout=self.timeout)
        return self._normalize_place(payload)

    @staticmethod
    def _normalize_place(place):
        if not isinstance(place, dict):
            raise ExternalServiceError("Google Places devolvió un club no válido.")

        display_name = place.get("displayName")
        location = place.get("location")
        if not isinstance(display_name, dict) or not isinstance(location, dict):
            raise ExternalServiceError("Google Places devolvió un club incompleto.")

        try:
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
        except (KeyError, TypeError, ValueError) as error:
            raise ExternalServiceError("Google Places devolvió coordenadas no válidas.") from error

        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise ExternalServiceError("Google Places devolvió coordenadas no válidas.")

        place_id = place.get("id")
        name = display_name.get("text")
        address = place.get("formattedAddress")
        if not all(isinstance(value, str) and value for value in (place_id, name, address)):
            raise ExternalServiceError("Google Places devolvió un club incompleto.")

        return {
            "place_id": place_id,
            "name": name,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
        }


def _validate_session_token(session_token: str | None):
    if session_token is not None and (
        not isinstance(session_token, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,36}", session_token)
    ):
        raise ValueError("La sesión de sugerencias no es válida.")
