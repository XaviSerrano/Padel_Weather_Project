# Tecnologías del proyecto

## Aplicación

| Tecnología | Uso | Implementación |
| --- | --- | --- |
| Python 3.10+ | Backend, integración con proveedores y lógica meteorológica | Código en `src/`, ejecutado con `python -m src.main`. |
| `http.server` (biblioteca estándar de Python) | API HTTP y servidor de la compilación frontend | Rutas JSON para búsqueda y previsión; en producción sirve `dist/`. No necesita un framework de servidor. |
| React 19 | Interfaz por componentes y estado interactivo | `web/src/App.tsx` renderiza búsqueda, resultados, controles y previsión. |
| TypeScript 5 | Tipos para datos de clubes, previsión y estados de la interfaz | Configuración estricta en `tsconfig.app.json`; `npm run typecheck` valida la aplicación. |
| Vite 7 | Servidor de desarrollo y compilación frontend | `vite.config.ts` usa `web/` como raíz, proxifica `/api` al backend y compila en `dist/`. |
| HTML5 y CSS3 | Estructura, accesibilidad y diseño adaptable de la interfaz | `web/index.html` define el punto de entrada; `web/styles.css` contiene los estilos responsive, importados desde `web/src/main.tsx`. |
| Node.js y npm | Entorno de desarrollo frontend, scripts y gestión de paquetes | Versiones mínimas en `README.md`; `package.json` define scripts y `package-lock.json` fija dependencias. |

## Fuentes de datos

| Tecnología / servicio | Uso | Implementación |
| --- | --- | --- |
| Google Places API (New) | Autocompletado, selección verificada y búsqueda de clubes | `src/extract/google_places_extractor.py` utiliza Autocomplete, Place Details y Text Search con FieldMask donde corresponde. La interfaz llama a `/api/clubs/autocomplete` y `/api/clubs/details`; comparte un token UUID de sesión de Autocomplete con Place Details. `GOOGLE_PLACES_API_KEY` solo se lee en el backend. Requiere habilitar los servicios necesarios en Google Cloud y puede tener costes por solicitud. |
| Open-Meteo Forecast API | Previsión por hora según latitud y longitud | `src/extract/weather_extractor.py` solicita temperatura, probabilidad de precipitación, viento y rachas en la zona horaria del club. |
| Google Fonts | Tipografías DM Sans y Manrope | Cargadas desde `web/index.html`; requieren conexión externa en el navegador. |

## Transporte y lógica

- **HTTP y JSON** comunican la interfaz y el backend: `GET /api/clubs/autocomplete`, `GET /api/clubs/details`, `POST /api/clubs/search` y `GET /api/weather`.
- El navegador consume la API con `fetch`; el proxy de Vite evita configurar CORS durante el desarrollo local.
- `src/services/club_service.py` y `src/services/weather_service.py` orquestan los extractores sin exponer claves al frontend.
- El backend carga las variables de `.env` al arrancar mediante `src/env.py`; las variables ya definidas en el entorno tienen prioridad. `.env.example` documenta nombres y valores de ejemplo sin secretos. Los umbrales son configurables y los resultados no confirman disponibilidad ni reservas.
- `src/extract/http_json.py` centraliza solicitudes JSON, timeouts, reintentos limitados y errores de proveedores.

## Calidad y ejecución

- **`unittest`** ejecuta pruebas Python con servicios externos simulados: `python -m unittest discover -s tests -v`.
- **TypeScript** valida tipos con `npm run typecheck`; `npm run build` tipa y compila.
- Dependencias Python: ninguna fuera de la biblioteca estándar.
- La aplicación no utiliza actualmente PostgreSQL, Playtomic, mapas interactivos ni autenticación.

## Comandos principales

```powershell
npm ci
npm run dev
npm run typecheck
npm run build
python -m unittest discover -s tests -v
python -m src.main
```
