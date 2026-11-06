import type { FormEvent, KeyboardEvent } from "react";
import { useEffect, useRef, useState } from "react";

interface Club {
  place_id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
}

interface Forecast {
  time: string;
  score: number;
  rating: string;
  conditions: string[];
  temperature_c: number;
  precipitation_probability_percent: number;
  wind_speed_kmh: number;
}

interface ClubSuggestion {
  place_id: string;
  name: string;
  address: string;
}

type CourtType = "indoor" | "outdoor";

const today = new Date();
const maxForecastDate = new Date(today);
maxForecastDate.setDate(maxForecastDate.getDate() + 6);
const tomorrow = new Date(today);
tomorrow.setDate(tomorrow.getDate() + 1);
const minDate = formatDate(today);
const maxDate = formatDate(maxForecastDate);

function App() {
  const [query, setQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState("");
  const [searchError, setSearchError] = useState(false);
  const [searching, setSearching] = useState(false);
  const [resolvingSuggestion, setResolvingSuggestion] = useState(false);
  const [suggestions, setSuggestions] = useState<ClubSuggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState("");
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [autocompleteEnabled, setAutocompleteEnabled] = useState(true);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [clubs, setClubs] = useState<Club[]>([]);
  const [selectedClub, setSelectedClub] = useState<Club | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [date, setDate] = useState(formatDate(tomorrow));
  const [courtType, setCourtType] = useState<CourtType>("outdoor");
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [forecastStatus, setForecastStatus] = useState("");
  const [forecastError, setForecastError] = useState(false);
  const placeDetailsController = useRef<AbortController | null>(null);
  const searchController = useRef<AbortController | null>(null);
  const autocompleteController = useRef<AbortController | null>(null);
  const sessionToken = useRef<string | null>(null);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (!autocompleteEnabled || selectedPlaceId || normalizedQuery.length < 3) {
      setSuggestions([]);
      setSuggestionsOpen(false);
      setSuggestionsLoading(false);
      setSuggestionsError("");
      setActiveSuggestionIndex(-1);
      return;
    }

    const controller = new AbortController();
    autocompleteController.current = controller;
    const timer = window.setTimeout(() => {
      setSuggestionsLoading(true);
      setSuggestionsError("");
      const params = new URLSearchParams({
        input: normalizedQuery,
        session_token: getSessionToken(sessionToken),
      });
      fetch(`/api/clubs/autocomplete?${params}`, { signal: controller.signal })
        .then((response) =>
          readResponse(response, (value) => parseSuggestionsPayload(value).suggestions),
        )
        .then((nextSuggestions) => {
          if (controller.signal.aborted) return;
          setSuggestions(nextSuggestions);
          setSuggestionsOpen(true);
          setActiveSuggestionIndex(-1);
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          setSuggestions([]);
          setSuggestionsOpen(false);
          setSuggestionsError(errorMessage(error, "No se pudieron cargar las sugerencias."));
        })
        .finally(() => {
          if (!controller.signal.aborted) setSuggestionsLoading(false);
        });
    }, 300);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [autocompleteEnabled, query, selectedPlaceId]);

  useEffect(() => {
    if (!selectedClub) return;

    const controller = new AbortController();
    const params = new URLSearchParams({
      latitude: String(selectedClub.latitude),
      longitude: String(selectedClub.longitude),
      date,
      court_type: courtType,
    });

    setForecasts([]);
    setSelectedTime(null);
    setForecastStatus("Consultando la previsión horaria…");
    setForecastError(false);

    fetch(`/api/weather?${params}`, { signal: controller.signal })
      .then((response) =>
        readResponse(response, (value) => parseForecastsPayload(value).forecasts),
      )
      .then((nextForecasts) => {
        setForecasts(nextForecasts);
        setForecastStatus(
          nextForecasts.length
            ? "Selecciona una hora para tenerla como referencia."
            : "No hay horas disponibles para esa fecha.",
        );
        setForecastError(nextForecasts.length === 0);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setForecastStatus(errorMessage(error, "No se pudo cargar la previsión."));
        setForecastError(true);
      });

    return () => controller.abort();
  }, [selectedClub, date, courtType]);

  async function searchClubs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = query.trim();
    if (!normalizedQuery || searching) return;

    setSearching(true);
    setAutocompleteEnabled(false);
    setSuggestionsOpen(false);
    autocompleteController.current?.abort();
    setSuggestionsLoading(false);
    setSearchStatus("Buscando clubes…");
    setSearchError(false);
    setClubs([]);
    setSelectedClub(null);
    if (selectedPlaceId) {
      setSelectedPlaceId(null);
    }
    sessionToken.current = null;
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    placeDetailsController.current?.abort();

    try {
      const nextClubs = await fetch("/api/clubs/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: normalizedQuery }),
        signal: controller.signal,
      }).then((response) => readResponse(response, parseClubsPayload));

      if (controller.signal.aborted) return;
      setClubs(nextClubs);
      setSearchStatus(
        nextClubs.length
          ? `${nextClubs.length} clubes encontrados.`
          : "No encontramos clubes. Prueba con otra búsqueda.",
      );
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      setSearchStatus(errorMessage(error, "No se pudo completar la búsqueda."));
      setSearchError(true);
    } finally {
      if (!controller.signal.aborted) setSearching(false);
    }
  }

  async function chooseSuggestion(suggestion: ClubSuggestion) {
    searchController.current?.abort();
    setSearching(false);
    placeDetailsController.current?.abort();
    const controller = new AbortController();
    placeDetailsController.current = controller;
    setAutocompleteEnabled(false);
    setSuggestionsOpen(false);
    setResolvingSuggestion(true);
    setSuggestionsError("");
    setSearchStatus("Verificando el club seleccionado…");
    setSearchError(false);
    setClubs([]);
    setSelectedClub(null);

    try {
      const params = new URLSearchParams({
        place_id: suggestion.place_id,
        session_token: getSessionToken(sessionToken),
      });
      sessionToken.current = null;
      const club = await fetch(`/api/clubs/details?${params}`, { signal: controller.signal })
        .then((response) => readResponse(response, parseClubDetailsPayload));
      if (controller.signal.aborted) return;
      setSelectedPlaceId(club.place_id);
      setQuery(club.name);
      setClubs([club]);
      setSearchStatus("Club verificado. Comprueba la dirección y consulta su previsión.");
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      setSuggestionsOpen(true);
      setAutocompleteEnabled(true);
      setSuggestionsError(errorMessage(error, "No se pudo verificar el club seleccionado."));
      setSearchStatus("No se pudo verificar el club. Puedes elegir otra sugerencia o buscar por texto.");
      setSearchError(true);
    } finally {
      if (!controller.signal.aborted) setResolvingSuggestion(false);
    }
  }

  function updateQuery(value: string) {
    searchController.current?.abort();
    setSearching(false);
    placeDetailsController.current?.abort();
    autocompleteController.current?.abort();
    setSuggestionsLoading(false);
    setResolvingSuggestion(false);
    setAutocompleteEnabled(true);
    setQuery(value);
    setSuggestions([]);
    setSuggestionsOpen(false);
    setActiveSuggestionIndex(-1);
    setSelectedPlaceId(null);
    setClubs([]);
    setSelectedClub(null);
    setSearchStatus("");
    setSearchError(false);
    setSuggestionsError("");
  }

  function handleAutocompleteKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && suggestions.length > 0) {
      event.preventDefault();
      setSuggestionsOpen(true);
      setActiveSuggestionIndex((index) => (index + 1) % suggestions.length);
    } else if (event.key === "ArrowUp" && suggestions.length > 0) {
      event.preventDefault();
      setSuggestionsOpen(true);
      setActiveSuggestionIndex((index) =>
        index <= 0 ? suggestions.length - 1 : index - 1,
      );
    } else if (event.key === "Enter" && activeSuggestionIndex >= 0 && suggestionsOpen) {
      event.preventDefault();
      void chooseSuggestion(suggestions[activeSuggestionIndex]);
    } else if (event.key === "Escape" && suggestionsOpen) {
      event.preventDefault();
      setSuggestionsOpen(false);
    }
  }

  function chooseClub(club: Club) {
    setSelectedClub(club);
    setSelectedTime(null);
    document.querySelector("#forecast-section")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <>
      <header className="topbar">
        <a className="brand" href="/" aria-label="Padel Weather, inicio">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>padel<span className="brand-light">weather</span></span>
        </a>
        <span className="topbar-note"><span className="live-dot" /> Tu próximo partido, con buen tiempo</span>
        <a className="about-link" href="#como-funciona">Cómo funciona <span aria-hidden="true">↗</span></a>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> EL TIEMPO TAMBIÉN JUEGA</div>
            <h1>Encuentra tu<br />mejor momento<br /><span>para jugar.</span></h1>
            <p>Busca un club y descubre qué horas tienen la previsión ideal para salir a pista.</p>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="sun-glow" />
            <div className="court court-back" />
            <div className="court court-front">
              <div className="court-net" />
              <div className="court-service court-service-left" />
              <div className="court-service court-service-right" />
              <div className="court-center" />
            </div>
            <div className="hero-ball" />
            <div className="weather-bubble bubble-sun"><span>☀</span> Elige tu hora</div>
            <div className="weather-bubble bubble-wind"><span>↗</span> Outdoor</div>
          </div>
        </section>

        <section className="search-panel" aria-labelledby="search-title">
          <div className="section-heading">
            <div>
              <span className="step-label">01 / ENCUENTRA TU CLUB</span>
              <h2 id="search-title">¿Dónde quieres jugar?</h2>
            </div>
            <span className="places-badge"><span aria-hidden="true">⌖</span> Busca por ciudad</span>
          </div>
          <form className="search-form" onSubmit={searchClubs}>
            <div className="autocomplete-wrap">
              <label className="search-input-wrap" htmlFor="club-query">
                <span className="search-icon" aria-hidden="true">⌕</span>
                <input
                  id="club-query"
                  name="query"
                  type="search"
                  maxLength={200}
                  placeholder="Nombre del club, ciudad o ambos"
                  autoComplete="off"
                  required
                  role="combobox"
                  aria-autocomplete="list"
                  aria-expanded={suggestionsOpen && suggestions.length > 0}
                  aria-controls="club-suggestions"
                  aria-activedescendant={
                    suggestionsOpen && activeSuggestionIndex >= 0
                      ? `club-suggestion-${activeSuggestionIndex}`
                      : undefined
                  }
                  value={query}
                  onChange={(event) => updateQuery(event.target.value)}
                  onKeyDown={handleAutocompleteKeyDown}
                  onFocus={() => {
                    if (suggestions.length > 0) setSuggestionsOpen(true);
                  }}
                  onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
                />
              </label>
              {suggestionsOpen && suggestions.length > 0 && (
                <div
                  id="club-suggestions"
                  className="suggestion-dropdown"
                  role="listbox"
                  aria-label="Centros sugeridos"
                >
                  {suggestions.map((suggestion, index) => (
                    <div
                      id={`club-suggestion-${index}`}
                      className={`suggestion-option${index === activeSuggestionIndex ? " is-active" : ""}`}
                      key={suggestion.place_id}
                      role="option"
                      aria-selected={index === activeSuggestionIndex}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => void chooseSuggestion(suggestion)}
                    >
                      <span className="suggestion-pin" aria-hidden="true">⌖</span>
                      <span className="suggestion-copy">
                        <strong>{suggestion.name}</strong>
                        {suggestion.address && <span>{suggestion.address}</span>}
                      </span>
                    </div>
                  ))}
                  <p className="places-attribution">Sugerencias de Google Maps</p>
                </div>
              )}
            </div>
            <button className="primary-button" type="submit" disabled={searching || resolvingSuggestion}>
              {searching ? "Buscando…" : resolvingSuggestion ? "Verificando…" : "Buscar clubes"}
              <span aria-hidden="true">→</span>
            </button>
          </form>
          <p className="search-guidance">
            Escribe al menos 3 letras y selecciona el resultado correcto. Ej.: «Padel Barcelona» o «Club X, Sabadell».
          </p>
          {(searchStatus || suggestionsLoading || suggestionsError ||
            (suggestionsOpen && suggestions.length === 0 && query.trim().length >= 3)) && (
            <p className={`status-message${searchError || suggestionsError ? " is-error" : ""}`} role="status" aria-live="polite">
              {suggestionsError ||
                searchStatus ||
                (suggestionsLoading
                  ? "Buscando sugerencias…"
                  : "No hay coincidencias. Añade la localidad o prueba la búsqueda por texto.")}
            </p>
          )}
          {clubs.length > 0 && (
            <div className="club-results" aria-live="polite">
              {clubs.map((club) => (
                <article className="club-card" key={club.place_id}>
                  <div><h3>{club.name}</h3><p>{club.address}</p></div>
                  <button type="button" onClick={() => chooseClub(club)}>Ver previsión →</button>
                </article>
              ))}
              <p className="places-attribution">Información de lugares proporcionada por Google Maps.</p>
            </div>
          )}
        </section>

        {selectedClub && (
          <section id="forecast-section" className="forecast-section" aria-labelledby="forecast-title">
            <div className="section-heading forecast-heading">
              <div>
                <span className="step-label">02 / ELIGE TU MOMENTO</span>
                <h2 id="forecast-title">La previsión en pista</h2>
              </div>
              <div className="forecast-controls">
                <label>
                  <span className="sr-only">Fecha</span>
                  <input
                    type="date"
                    min={minDate}
                    max={maxDate}
                    value={date}
                    onChange={(event) => setDate(event.target.value)}
                  />
                </label>
                <label className="court-select">
                  <span className="sr-only">Tipo de pista</span>
                  <select
                    value={courtType}
                    onChange={(event) => {
                      const nextCourtType = event.target.value;
                      if (nextCourtType === "indoor" || nextCourtType === "outdoor") {
                        setCourtType(nextCourtType);
                      }
                    }}
                  >
                    <option value="outdoor">Outdoor</option>
                    <option value="indoor">Indoor</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="selected-club"><strong>{selectedClub.name}</strong> · {selectedClub.address}</div>
            <div className="forecast-legend">
              <span><span className="legend-dot green" /> Mejor previsión primero</span>
              <span>Desliza para ver todas las horas</span>
            </div>
            <p className={`status-message${forecastError ? " is-error" : ""}`} role="status" aria-live="polite">
              {forecastStatus}
            </p>
            {forecasts.length > 0 && (
              <div className="forecast-grid">
                {forecasts.map((forecast) => (
                  <button
                    className={`forecast-card${selectedTime === forecast.time ? " is-selected" : ""}`}
                    type="button"
                    key={forecast.time}
                    aria-pressed={selectedTime === forecast.time}
                    aria-label={`${forecast.time}, ${forecast.rating}. Seleccionar hora.`}
                    onClick={() => {
                      setSelectedTime(forecast.time);
                      setForecastStatus(`Has seleccionado las ${forecast.time} como hora de referencia.`);
                    }}
                  >
                    <div className="forecast-time">
                      <strong>{forecast.time}</strong><span>{forecast.score}/100</span>
                    </div>
                    <div className="forecast-score">ÍNDICE METEOROLÓGICO</div>
                    <p className={`forecast-rating${forecast.score < 70 ? " is-warning" : ""}`}>
                      {forecast.rating}
                    </p>
                    <div className="weather-metrics">
                      <span>🌡 {Math.round(forecast.temperature_c)} °C</span>
                      <span>↗ {Math.round(forecast.wind_speed_kmh)} km/h</span>
                      <span>☂ {Math.round(forecast.precipitation_probability_percent)} %</span>
                    </div>
                    <p className="forecast-conditions">{forecast.conditions.join(" · ")}</p>
                  </button>
                ))}
              </div>
            )}
            <div className="availability-note">
              <span className="note-icon" aria-hidden="true">i</span>
              <p><strong>Una buena previsión no confirma una pista libre.</strong> Elige una hora como referencia; la disponibilidad no está conectada a ningún sistema de reservas.</p>
            </div>
          </section>
        )}

        <section id="how-it-works" className="how-section">
          <div id="como-funciona" className="how-intro">
            <span className="step-label">SENCILLO COMO UN BUEN GLOBO</span>
            <h2>De la búsqueda<br />a la pista.</h2>
          </div>
          <div className="how-steps">
            <article className="how-step">
              <span className="step-number">01</span>
              <div><h3>Encuentra un club</h3><p>Busca por nombre o ciudad y elige dónde jugar.</p></div>
            </article>
            <article className="how-step">
              <span className="step-number">02</span>
              <div><h3>Elige fecha y pista</h3><p>La previsión se adapta a la ubicación y al tipo de pista.</p></div>
            </article>
            <article className="how-step">
              <span className="step-number">03</span>
              <div><h3>Escoge tu hora ideal</h3><p>Compara temperatura, viento y probabilidad de lluvia.</p></div>
            </article>
          </div>
        </section>
      </main>

      <footer className="footer">
        <a className="brand footer-brand" href="/">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>padel<span className="brand-light">weather</span></span>
        </a>
        <p>Hecho para que el tiempo no te deje en la red.</p>
        <span className="footer-source">Previsión meteorológica por Open-Meteo</span>
      </footer>
    </>
  );
}

async function readResponse<T>(response: Response, parse: (value: unknown) => T): Promise<T> {
  const data: unknown = await response.json();
  if (!response.ok) {
    const message =
      isRecord(data) && typeof data.error === "string"
        ? data.error
        : "La solicitud no se pudo completar.";
    throw new Error(message);
  }
  return parse(data);
}

function parseClubsPayload(value: unknown): Club[] {
  if (!isRecord(value) || !Array.isArray(value.clubs)) {
    throw new Error("La respuesta de búsqueda no tiene un formato válido.");
  }
  return value.clubs.map(parseClubPayload);
}

function parseClubPayload(value: unknown): Club {
  if (
    !isRecord(value) ||
    typeof value.place_id !== "string" ||
    typeof value.name !== "string" ||
    typeof value.address !== "string" ||
    typeof value.latitude !== "number" ||
    typeof value.longitude !== "number"
  ) {
    throw new Error("La respuesta contiene un club con datos no válidos.");
  }
  return {
    place_id: value.place_id,
    name: value.name,
    address: value.address,
    latitude: value.latitude,
    longitude: value.longitude,
  };
}

function parseClubDetailsPayload(value: unknown): Club {
  if (!isRecord(value)) {
    throw new Error("La respuesta del club no tiene un formato válido.");
  }
  return parseClubPayload(value.club);
}

function parseSuggestionsPayload(value: unknown): { suggestions: ClubSuggestion[] } {
  if (!isRecord(value) || !Array.isArray(value.suggestions)) {
    throw new Error("La respuesta de sugerencias no tiene un formato válido.");
  }
  const suggestions = value.suggestions.map((suggestion): ClubSuggestion => {
    if (
      !isRecord(suggestion) ||
      typeof suggestion.place_id !== "string" ||
      typeof suggestion.name !== "string" ||
      typeof suggestion.address !== "string"
    ) {
      throw new Error("La respuesta contiene una sugerencia no válida.");
    }
    return {
      place_id: suggestion.place_id,
      name: suggestion.name,
      address: suggestion.address,
    };
  });
  return { suggestions };
}

function parseForecastsPayload(value: unknown): { forecasts: Forecast[] } {
  if (!isRecord(value) || !Array.isArray(value.forecasts)) {
    throw new Error("La respuesta meteorológica no tiene un formato válido.");
  }
  const forecasts = value.forecasts.map((forecast): Forecast => {
    if (
      !isRecord(forecast) ||
      typeof forecast.time !== "string" ||
      typeof forecast.score !== "number" ||
      typeof forecast.rating !== "string" ||
      !Array.isArray(forecast.conditions) ||
      !forecast.conditions.every((condition) => typeof condition === "string") ||
      typeof forecast.temperature_c !== "number" ||
      typeof forecast.precipitation_probability_percent !== "number" ||
      typeof forecast.wind_speed_kmh !== "number"
    ) {
      throw new Error("La respuesta contiene una previsión con datos no válidos.");
    }
    return {
      time: forecast.time,
      score: forecast.score,
      rating: forecast.rating,
      conditions: forecast.conditions,
      temperature_c: forecast.temperature_c,
      precipitation_probability_percent: forecast.precipitation_probability_percent,
      wind_speed_kmh: forecast.wind_speed_kmh,
    };
  });
  return { forecasts };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getSessionToken(sessionToken: { current: string | null }): string {
  if (!sessionToken.current) {
    sessionToken.current = window.crypto.randomUUID();
  }
  return sessionToken.current;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default App;
