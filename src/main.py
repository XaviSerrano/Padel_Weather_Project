import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from src.config import WeatherThresholds
from src.env import load_env_file
from src.errors import ConfigurationError, ExternalServiceError
from src.extract.weather_extractor import OpenMeteoExtractor
from src.services.club_service import ClubService
from src.services.weather_service import WeatherService


DIST_ROOT = Path(__file__).resolve().parent.parent / "dist"
MAX_BODY_SIZE = 4096


def create_handler(club_service, weather_service):
    class PadelWeatherHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_url = urlsplit(self.path)
            if parsed_url.path == "/":
                return self._send_file(DIST_ROOT / "index.html", "text/html; charset=utf-8")
            if parsed_url.path.startswith("/assets/"):
                return self._send_asset(parsed_url.path)
            if parsed_url.path == "/api/health":
                return self._send_json(200, {"status": "ok"})
            if parsed_url.path == "/api/clubs/autocomplete":
                return self._get_club_suggestions(parse_qs(parsed_url.query))
            if parsed_url.path == "/api/clubs/details":
                return self._get_club_details(parse_qs(parsed_url.query))
            if parsed_url.path == "/api/weather":
                return self._get_weather(parse_qs(parsed_url.query))
            return self._send_json(404, {"error": "No se encontró esa ruta."})

        def do_POST(self):
            if urlsplit(self.path).path != "/api/clubs/search":
                return self._send_json(404, {"error": "No se encontró esa ruta."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._send_json(400, {"error": "El tamaño de la solicitud no es válido."})
            if length <= 0 or length > MAX_BODY_SIZE:
                return self._send_json(400, {"error": "La solicitud debe tener un tamaño válido."})
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._send_json(400, {"error": "El cuerpo debe ser JSON válido."})
            if not isinstance(body, dict):
                return self._send_json(400, {"error": "El cuerpo debe ser un objeto JSON."})
            try:
                clubs = club_service.search(body.get("query"))
            except ValueError as error:
                return self._send_json(400, {"error": str(error)})
            except ConfigurationError as error:
                return self._send_json(503, {"error": str(error)})
            except ExternalServiceError as error:
                return self._send_json(502, {"error": str(error)})
            return self._send_json(200, {"clubs": clubs})

        def _get_weather(self, query):
            try:
                latitude = float(_single(query, "latitude"))
                longitude = float(_single(query, "longitude"))
                selected_date = _single(query, "date")
                court_type = _single(query, "court_type")
                forecasts = weather_service.for_date(
                    latitude, longitude, selected_date, court_type
                )
            except (TypeError, ValueError) as error:
                return self._send_json(400, {"error": str(error) or "Parámetros no válidos."})
            except ExternalServiceError as error:
                return self._send_json(502, {"error": str(error)})
            return self._send_json(200, {"forecasts": forecasts})

        def _get_club_suggestions(self, query):
            try:
                suggestions = club_service.autocomplete(
                    _single(query, "input"),
                    _optional_single(query, "session_token"),
                )
            except ValueError as error:
                return self._send_json(400, {"error": str(error)})
            except ConfigurationError as error:
                return self._send_json(503, {"error": str(error)})
            except ExternalServiceError as error:
                return self._send_json(502, {"error": str(error)})
            return self._send_json(200, {"suggestions": suggestions})

        def _get_club_details(self, query):
            try:
                club = club_service.get_place(
                    _single(query, "place_id"),
                    _optional_single(query, "session_token"),
                )
            except ValueError as error:
                return self._send_json(400, {"error": str(error)})
            except ConfigurationError as error:
                return self._send_json(503, {"error": str(error)})
            except ExternalServiceError as error:
                return self._send_json(502, {"error": str(error)})
            return self._send_json(200, {"club": club})

        def _send_file(self, path, content_type):
            try:
                content = path.read_bytes()
            except OSError:
                return self._send_json(
                    500,
                    {"error": "No se encontró la interfaz compilada. Ejecuta npm run build."},
                )
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def _send_asset(self, request_path):
            relative_path = Path(unquote(request_path.removeprefix("/assets/")))
            asset_path = (DIST_ROOT / "assets" / relative_path).resolve()
            assets_root = (DIST_ROOT / "assets").resolve()
            if not asset_path.is_relative_to(assets_root) or not asset_path.is_file():
                return self._send_json(404, {"error": "No se encontró ese recurso."})
            content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
            return self._send_file(asset_path, content_type)

        def _send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

    return PadelWeatherHandler


def _single(query, name):
    values = query.get(name)
    if not values or len(values) != 1 or not values[0]:
        raise ValueError(f"Falta el parámetro {name}.")
    return values[0]


def _optional_single(query, name):
    values = query.get(name)
    if values is None:
        return None
    if len(values) != 1 or not values[0]:
        raise ValueError(f"El parámetro {name} no es válido.")
    return values[0]


def main():
    load_env_file(Path(__file__).resolve().parent.parent / ".env")
    thresholds = WeatherThresholds.from_environment()
    club_service = ClubService(os.getenv("GOOGLE_PLACES_API_KEY", "").strip())
    weather_service = WeatherService(OpenMeteoExtractor(), thresholds)
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), create_handler(club_service, weather_service))
    print(f"Padel Weather disponible en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
