"""Where the person is: detected from their IP, or searched for by name.

Both lookups go to free, keyless public APIs, which means each visitor's IP is
sent to ipwho.is. Once deployed behind Cloudflare/Vercel/CloudFront, prefer a
resolver that reads the edge's geo headers (CF-IPCity etc.) instead — no third
party, no rate limit. Swap by overriding get_location_service().
"""

import ipaddress
import logging
from functools import lru_cache
from typing import Protocol

import httpx
from fastapi import Request

from app.models import Location
from app.ttl_cache import TTLCache

log = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(3.0)


class LocationService(Protocol):
    def from_ip(self, ip: str | None) -> Location | None:
        """Approximate location for an IP. None = the caller's own public IP."""
        ...

    def search(self, query: str) -> list[Location]:
        """Places matching a typed name, for manually changing location."""
        ...


def client_ip(request: Request) -> str | None:
    """The visitor's public IP, or None when the request came from a private network.

    X-Forwarded-For is spoofable, but the only thing a spoofer controls is their
    own detected location, so trusting it is harmless here.
    """
    forwarded = request.headers.get("x-forwarded-for")
    candidates = [forwarded.split(",")[0].strip()] if forwarded else []
    if request.client:
        candidates.append(request.client.host)
    for raw in candidates:
        try:
            if ipaddress.ip_address(raw).is_global:
                return raw
        except ValueError:
            continue
    # In local dev every request is 127.0.0.1 (via the Vite proxy). Returning
    # None makes the lookup resolve this machine's public IP, which is the
    # developer's real location — so detection is testable without deploying.
    return None


def _label(*parts: str | None) -> str:
    return ", ".join(p for p in parts if p)


class PublicLocationService:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self._ip_cache: TTLCache[str, Location | None] = TTLCache(ttl_seconds=6 * 3600)
        self._search_cache: TTLCache[str, list[Location] | None] = TTLCache(
            ttl_seconds=24 * 3600
        )

    def from_ip(self, ip: str | None) -> Location | None:
        return self._ip_cache.get_or_set(ip or "self", lambda: self._lookup_ip(ip))

    def _lookup_ip(self, ip: str | None) -> Location | None:
        try:
            res = self.client.get(f"https://ipwho.is/{ip or ''}")
            res.raise_for_status()
            data = res.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("IP location lookup failed: %s", e)
            return None
        if not data.get("success") or data.get("latitude") is None:
            log.warning(
                "IP location lookup returned no result: %s", data.get("message")
            )
            return None
        return Location(
            label=_label(data.get("city"), data.get("region"))
            or data.get("country")
            or "Your area",
            city=data.get("city"),
            region=data.get("region"),
            country_code=data.get("country_code"),
            latitude=data["latitude"],
            longitude=data["longitude"],
            source="ip",
        )

    def search(self, query: str) -> list[Location]:
        q = query.strip()
        if len(q) < 2:
            return []
        return self._search_cache.get_or_set(q.lower(), lambda: self._geocode(q)) or []

    def _geocode(self, q: str) -> list[Location] | None:
        try:
            res = self.client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": q, "count": 6, "language": "en", "format": "json"},
            )
            res.raise_for_status()
            results = res.json().get("results") or []
        except (httpx.HTTPError, ValueError) as e:
            log.warning("Place search failed: %s", e)
            return None
        return [
            Location(
                label=_label(r.get("name"), r.get("admin1") or r.get("country")),
                city=r.get("name"),
                region=r.get("admin1"),
                country_code=r.get("country_code"),
                latitude=r["latitude"],
                longitude=r["longitude"],
                source="manual",
            )
            for r in results
        ]


@lru_cache
def get_location_service() -> LocationService:
    return PublicLocationService()
