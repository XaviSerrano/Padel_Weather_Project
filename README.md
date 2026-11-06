# Padel Weather

Aplicación web que relaciona clubes de pádel con la previsión meteorológica horaria. La disponibilidad se elige manualmente: no está conectada a Playtomic ni representa pistas libres confirmadas.

## Requisitos

- Python 3.10 o posterior.
- Node.js 20.19+ o 22.12+ y npm.
- Una clave de Google Places API (New), con Autocomplete, Place Details y Text Search habilitados. Google puede exigir una cuenta de facturación y aplicar costes según el uso.

## Desarrollo local

Abre dos terminales en la raíz del proyecto. Copia `.env.example` a `.env` y añade la clave en `GOOGLE_PLACES_API_KEY` dentro de `.env`. Este archivo está ignorado por Git; no guardes claves en `.env.example`. En la primera terminal, arranca el backend:

```powershell
python -m src.main
```

En la segunda, instala dependencias e inicia Vite:

```powershell
npm ci
npm run dev
```

Abre <http://127.0.0.1:5173>. Vite envía las llamadas `/api` al backend en `http://127.0.0.1:8000`. Si el backend utiliza otro host, configura `VITE_BACKEND_URL` antes de iniciar Vite.

## Producción local

```powershell
npm ci
npm run build
python -m src.main
```

El backend sirve la compilación de `dist/` en <http://127.0.0.1:8000>. La clave se usa únicamente en el backend; no se envía al navegador. El backend carga `.env` al arrancar; las variables ya definidas en el entorno tienen prioridad. Reinícialo después de modificar el archivo.

Puedes cambiar el puerto con `PORT` y ajustar la valoración meteorológica con estas variables opcionales:

| Variable | Valor por defecto | Uso |
| --- | ---: | --- |
| `PADEL_MODERATE_WIND_KMH` | 15 | Umbral de viento moderado |
| `PADEL_HIGH_WIND_KMH` | 25 | Umbral de viento fuerte |
| `PADEL_RAIN_PROBABILITY_PERCENT` | 40 | Umbral de posible lluvia |
| `PADEL_MIN_TEMP_C` | 10 | Temperatura mínima de confort |
| `PADEL_MAX_TEMP_C` | 32 | Temperatura máxima de confort |

La API de previsión usa Open-Meteo y devuelve horas locales del club. Los resultados se ordenan por una puntuación orientativa; las pistas indoor no reciben penalizaciones por viento, lluvia o temperatura.

## Pruebas y verificaciones

Las pruebas Python usan respuestas simuladas y no hacen llamadas externas:

```powershell
python -m unittest discover -s tests -v
npm run typecheck
npm run build
```

## Alcance actual

- Búsqueda de clubes con Google Places Text Search.
- Sugerencias de Google Places Autocomplete al escribir un club o una localidad; seleccionar una sugerencia verifica el lugar antes de consultar su previsión.
- Busca por nombre del club, localidad o ambos (por ejemplo, «Padel Barcelona» o «Club X, Sabadell»). Escribe al menos tres caracteres y selecciona la sugerencia para evitar confundir centros con nombres parecidos.
- Previsión horaria de siete días con Open-Meteo.
- Selección manual de una hora de referencia y distinción entre pista indoor y outdoor.
- Sin persistencia de los datos de Google Places; se conservan solo en memoria durante la sesión del navegador.
- Sin mapa, reservas, integración con Playtomic ni base de datos PostgreSQL.

Consulta [TECH.md](./TECH.md) para el inventario de tecnologías y cómo se integran.
