import json
import unittest
from unittest.mock import patch

from src.errors import ExternalServiceError
from src.extract.google_places_extractor import (
    GOOGLE_PLACES_AUTOCOMPLETE_FIELD_MASK,
    GOOGLE_PLACES_AUTOCOMPLETE_URL,
    GOOGLE_PLACES_DETAILS_URL,
    GOOGLE_PLACES_FIELD_MASK,
    GOOGLE_PLACES_SEARCH_URL,
    GOOGLE_PLACE_DETAILS_FIELD_MASK,
    GooglePlacesExtractor,
)


class GooglePlacesExtractorTests(unittest.TestCase):
    @patch("src.extract.google_places_extractor.request_json")
    def test_search_builds_request_and_normalizes_clubs(self, request_json):
        request_json.return_value = {
            "places": [
                {
                    "id": "place-123",
                    "displayName": {"text": "Club Padel"},
                    "formattedAddress": "Barcelona, España",
                    "location": {"latitude": 41.39, "longitude": 2.16},
                }
            ]
        }

        clubs = GooglePlacesExtractor("secret-key").search("  pádel Barcelona ")

        self.assertEqual(
            clubs,
            [
                {
                    "place_id": "place-123",
                    "name": "Club Padel",
                    "address": "Barcelona, España",
                    "latitude": 41.39,
                    "longitude": 2.16,
                }
            ],
        )
        request, service = request_json.call_args.args[:2]
        self.assertEqual(request.full_url, GOOGLE_PLACES_SEARCH_URL)
        self.assertEqual(request.get_header("X-goog-api-key"), "secret-key")
        self.assertEqual(request.get_header("X-goog-fieldmask"), GOOGLE_PLACES_FIELD_MASK)
        self.assertEqual(service, "Google Places")
        self.assertIn(b'"textQuery": "p\\u00e1del Barcelona"', request.data)

    def test_search_rejects_empty_query(self):
        with self.assertRaisesRegex(ValueError, "entre 1 y 200"):
            GooglePlacesExtractor("secret-key").search(" ")

    @patch("src.extract.google_places_extractor.request_json")
    def test_autocomplete_requests_spanish_suggestions(self, request_json):
        request_json.return_value = {
            "suggestions": [
                {
                    "placePrediction": {
                        "placeId": "place-123",
                        "text": {"text": "Club Padel, Barcelona"},
                        "structuredFormat": {
                            "mainText": {"text": "Club Padel"},
                            "secondaryText": {"text": "Barcelona, España"},
                        },
                    }
                }
            ]
        }

        suggestions = GooglePlacesExtractor("secret-key").autocomplete(
            " Padel Barcelona ", "session-123"
        )

        self.assertEqual(
            suggestions,
            [
                {
                    "place_id": "place-123",
                    "name": "Club Padel",
                    "address": "Barcelona, España",
                }
            ],
        )
        request, service = request_json.call_args.args[:2]
        self.assertEqual(request.full_url, GOOGLE_PLACES_AUTOCOMPLETE_URL)
        self.assertEqual(request.get_header("X-goog-api-key"), "secret-key")
        self.assertEqual(
            request.get_header("X-goog-fieldmask"),
            GOOGLE_PLACES_AUTOCOMPLETE_FIELD_MASK,
        )
        self.assertEqual(
            json.loads(request.data),
            {
                "input": "Padel Barcelona",
                "includedRegionCodes": ["es"],
                "languageCode": "es",
                "sessionToken": "session-123",
            },
        )
        self.assertEqual(service, "Google Places Autocomplete")

    def test_autocomplete_requires_three_characters(self):
        with self.assertRaisesRegex(ValueError, "entre 3 y 200"):
            GooglePlacesExtractor("secret-key").autocomplete("ab")

    def test_autocomplete_rejects_unsafe_session_tokens(self):
        with self.assertRaisesRegex(ValueError, "sesión de sugerencias"):
            GooglePlacesExtractor("secret-key").autocomplete("padel", "not a safe token")

    @patch("src.extract.google_places_extractor.request_json")
    def test_get_place_looks_up_full_club_details(self, request_json):
        request_json.return_value = {
            "id": "place/123",
            "displayName": {"text": "Club Padel"},
            "formattedAddress": "Barcelona, España",
            "location": {"latitude": 41.39, "longitude": 2.16},
        }

        club = GooglePlacesExtractor("secret-key").get_place("place/123", "session-123")

        self.assertEqual(club["place_id"], "place/123")
        request, service = request_json.call_args.args[:2]
        self.assertEqual(
            request.full_url,
            f"{GOOGLE_PLACES_DETAILS_URL}/place%2F123?sessionToken=session-123",
        )
        self.assertEqual(request.get_header("X-goog-fieldmask"), GOOGLE_PLACE_DETAILS_FIELD_MASK)
        self.assertEqual(service, "Google Places Details")

    @patch("src.extract.google_places_extractor.request_json")
    def test_search_rejects_invalid_coordinates(self, request_json):
        request_json.return_value = {
            "places": [
                {
                    "id": "place-123",
                    "displayName": {"text": "Club Padel"},
                    "formattedAddress": "Barcelona, España",
                    "location": {"latitude": 200, "longitude": 2.16},
                }
            ]
        }

        with self.assertRaisesRegex(ExternalServiceError, "coordenadas no válidas"):
            GooglePlacesExtractor("secret-key").search("pádel Barcelona")


if __name__ == "__main__":
    unittest.main()
