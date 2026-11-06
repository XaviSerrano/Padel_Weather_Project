from src.errors import ConfigurationError
from src.extract.google_places_extractor import GooglePlacesExtractor


class ClubService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str):
        return self._extractor().search(query)

    def autocomplete(self, query: str, session_token: str | None = None):
        return self._extractor().autocomplete(query, session_token)

    def get_place(self, place_id: str, session_token: str | None = None):
        return self._extractor().get_place(place_id, session_token)

    def _extractor(self):
        if not self.api_key:
            raise ConfigurationError(
                "Falta GOOGLE_PLACES_API_KEY. Configura la clave de Places API en el entorno."
            )
        return GooglePlacesExtractor(self.api_key)
