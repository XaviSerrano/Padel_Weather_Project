import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.errors import ExternalServiceError


def request_json(request: Request, service: str, timeout: float = 10, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ExternalServiceError(f"{service} devolvió una respuesta JSON no válida.")
            return payload
        except HTTPError as error:
            transient = error.code == 429 or 500 <= error.code < 600
            if transient and attempt < retries:
                time.sleep(min(0.25 * (2 ** attempt), 2))
                continue
            detail = _provider_error(error.read())
            suffix = f": {detail}" if detail else ""
            raise ExternalServiceError(
                f"{service} devolvió HTTP {error.code}{suffix}"
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt < retries:
                time.sleep(min(0.25 * (2 ** attempt), 2))
                continue
            raise ExternalServiceError(f"No se pudo conectar con {service}: {error}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExternalServiceError(f"{service} devolvió una respuesta JSON no válida.") from error


def _provider_error(body: bytes):
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"][:300]
    return ""
