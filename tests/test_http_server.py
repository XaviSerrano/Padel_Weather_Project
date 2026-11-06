import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from src.config import WeatherThresholds
from src.extract.weather_extractor import OpenMeteoExtractor
from src.main import create_handler
from src.services.club_service import ClubService
from src.services.weather_service import WeatherService


class HttpServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.dist_root = Path(self.temporary_directory.name)
        (self.dist_root / "assets").mkdir()
        (self.dist_root / "index.html").write_text("<html>Padel Weather</html>", encoding="utf-8")
        (self.dist_root / "assets" / "app.js").write_text("console.log('app');", encoding="utf-8")
        self.dist_root_patch = patch("src.main.DIST_ROOT", self.dist_root)
        self.dist_root_patch.start()

        self.club_service = ClubService("")
        handler = create_handler(
            self.club_service,
            WeatherService(OpenMeteoExtractor(), WeatherThresholds()),
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.dist_root_patch.stop()
        self.temporary_directory.cleanup()

    def test_serves_production_html_and_assets(self):
        with urlopen(self.base_url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"<html>Padel Weather</html>")

        with urlopen(f"{self.base_url}/assets/app.js", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/javascript")
            self.assertEqual(response.read(), b"console.log('app');")

    def test_health_route_returns_json(self):
        with urlopen(f"{self.base_url}/api/health", timeout=5) as response:
            self.assertEqual(json.loads(response.read()), {"status": "ok"})

    def test_club_autocomplete_and_details_validate_requests(self):
        for path in ("/api/clubs/autocomplete", "/api/clubs/details"):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as response:
                    urlopen(f"{self.base_url}{path}", timeout=5)
                self.assertEqual(response.exception.code, 400)
                response.exception.close()

        with self.assertRaises(HTTPError) as missing_key:
            urlopen(
                f"{self.base_url}/api/clubs/autocomplete?input=padel%20Barcelona",
                timeout=5,
            )
        self.assertEqual(missing_key.exception.code, 503)
        missing_key.exception.close()

    def test_club_autocomplete_and_details_return_selected_place(self):
        suggestions = [
            {"place_id": "p1", "name": "Padel Club", "address": "Barcelona, España"}
        ]
        club = {
            "place_id": "p1",
            "name": "Padel Club",
            "address": "Barcelona, España",
            "latitude": 41.39,
            "longitude": 2.16,
        }
        with patch.object(self.club_service, "autocomplete", return_value=suggestions) as autocomplete:
            with urlopen(
                f"{self.base_url}/api/clubs/autocomplete?input=Padel&session_token=session-123",
                timeout=5,
            ) as response:
                self.assertEqual(json.loads(response.read()), {"suggestions": suggestions})
            autocomplete.assert_called_once_with("Padel", "session-123")

        with patch.object(self.club_service, "get_place", return_value=club) as get_place:
            with urlopen(
                f"{self.base_url}/api/clubs/details?place_id=p1&session_token=session-123",
                timeout=5,
            ) as response:
                self.assertEqual(json.loads(response.read()), {"club": club})
            get_place.assert_called_once_with("p1", "session-123")

    def test_missing_asset_and_missing_google_key_are_reported(self):
        with self.assertRaises(HTTPError) as missing_asset:
            urlopen(f"{self.base_url}/assets/%2e%2e/index.html", timeout=5)
        self.assertEqual(missing_asset.exception.code, 404)
        missing_asset.exception.close()

        request = Request(
            f"{self.base_url}/api/clubs/search",
            data=json.dumps({"query": "pádel Barcelona"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as missing_key:
            urlopen(request, timeout=5)
        self.assertEqual(missing_key.exception.code, 503)
        payload = json.loads(missing_key.exception.read())
        missing_key.exception.close()
        self.assertIn("GOOGLE_PLACES_API_KEY", payload["error"])


if __name__ == "__main__":
    unittest.main()
