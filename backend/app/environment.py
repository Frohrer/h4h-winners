"""Current conditions at a location, passed to the recommender with each request.

Open-Meteo is free and keyless. Current conditions (not climate averages) are
used because they're what someone's hair is dealing with today; a routine-level
recommender may later want seasonal normals as well.
"""

import logging
from functools import lru_cache
from typing import Protocol

import httpx

from app.models import DewPointBand, Environment
from app.ttl_cache import TTLCache

log = logging.getLogger(__name__)

# Dew point bands commonly used in curly-hair care (roughly <40°F, 40-60°F, >60°F).
DRY_BELOW_C = 4.0
HUMID_ABOVE_C = 16.0

ADVICE: dict[DewPointBand, str] = {
    "dry": "The air is dry. Glycerin-heavy products can pull moisture out of your hair, so seal with a butter or oil.",
    "comfortable": "Conditions are easy on most products, including ones with glycerin.",
    "humid": "The air is humid, so expect more frizz and puffiness. Firmer-hold gels and anti-frizz products help.",
}


def dew_point_band(dew_point_c: float) -> DewPointBand:
    if dew_point_c < DRY_BELOW_C:
        return "dry"
    if dew_point_c > HUMID_ABOVE_C:
        return "humid"
    return "comfortable"


class EnvironmentProvider(Protocol):
    def current(self, latitude: float, longitude: float) -> Environment | None: ...


class OpenMeteoEnvironment:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=httpx.Timeout(3.0))
        # Rounding to ~10 km cells lets nearby visitors share a cached reading.
        self._cache: TTLCache[tuple[float, float], Environment | None] = TTLCache(
            ttl_seconds=30 * 60
        )

    def current(self, latitude: float, longitude: float) -> Environment | None:
        key = (round(latitude, 1), round(longitude, 1))
        return self._cache.get_or_set(key, lambda: self._fetch(*key))

    def _fetch(self, latitude: float, longitude: float) -> Environment | None:
        try:
            res = self.client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,relative_humidity_2m,dew_point_2m,uv_index",
                },
            )
            res.raise_for_status()
            now = res.json()["current"]
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning("Weather lookup failed: %s", e)
            return None
        band = dew_point_band(now["dew_point_2m"])
        return Environment(
            temperature_c=now["temperature_2m"],
            relative_humidity_pct=now["relative_humidity_2m"],
            dew_point_c=now["dew_point_2m"],
            uv_index=now.get("uv_index"),
            dew_point_band=band,
            advice=ADVICE[band],
        )


@lru_cache
def get_environment_provider() -> EnvironmentProvider:
    return OpenMeteoEnvironment()
