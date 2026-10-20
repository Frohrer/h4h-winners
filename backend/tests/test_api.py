import httpx
import pytest
from fastapi.testclient import TestClient

from app.catalog import get_catalog
from app.environment import (
    OpenMeteoEnvironment,
    dew_point_band,
    get_environment_provider,
)
from app.location import PublicLocationService, client_ip, get_location_service
from app.main import app
from app.models import (
    Environment,
    Location,
    Recommendation,
    RecommendationRequest,
    SimilarProduct,
)
from app.recommender import Ranking, get_recommender

client = TestClient(app)
catalog = get_catalog()

PHILLY = Location(
    label="Philadelphia, Pennsylvania",
    city="Philadelphia",
    region="Pennsylvania",
    country_code="US",
    latitude=39.95,
    longitude=-75.16,
    source="ip",
)


def make_env(dew_point_c: float) -> Environment:
    return Environment(
        temperature_c=25,
        relative_humidity_pct=80,
        dew_point_c=dew_point_c,
        dew_point_band=dew_point_band(dew_point_c),
        advice="test",
    )


class FakeLocations:
    def __init__(self):
        self.ips: list[str | None] = []

    def from_ip(self, ip):
        self.ips.append(ip)
        return PHILLY

    def search(self, query):
        return [PHILLY.model_copy(update={"source": "manual"})] if query else []


class FakeEnvironment:
    def __init__(self, dew_point_c: float = 20):
        self.dew_point_c = dew_point_c
        self.calls: list[tuple[float, float]] = []

    def current(self, latitude, longitude):
        self.calls.append((latitude, longitude))
        return make_env(self.dew_point_c)


@pytest.fixture(autouse=True)
def no_network():
    """Every test runs against fakes; the real providers are tested via MockTransport below."""
    locations, environment = FakeLocations(), FakeEnvironment()
    app.dependency_overrides[get_location_service] = lambda: locations
    app.dependency_overrides[get_environment_provider] = lambda: environment
    yield locations, environment
    app.dependency_overrides.clear()


# --- seed data integrity -------------------------------------------------------
# The UI renders straight from these records, so a dangling id or unknown hair
# type shows up as a crash or a blank section rather than a clear error.


def test_every_formula_ingredient_exists():
    for product in catalog.products.values():
        for entry in product.formula:
            assert entry.ingredient_id in catalog.ingredients, (
                product.id,
                entry.ingredient_id,
            )


def test_every_product_hair_type_is_known():
    codes = {h.code for h in catalog.hair_types}
    for product in catalog.products.values():
        assert set(product.hair_types) <= codes, product.id


def test_every_product_has_a_listing():
    for product in catalog.products.values():
        assert product.listings, product.id


# --- routes --------------------------------------------------------------------


def test_hair_types_cover_1a_to_4c():
    codes = [h["code"] for h in client.get("/api/hair-types").json()]
    assert codes == [f"{n}{l}" for n in "1234" for l in "ABC"]


def test_product_search_by_name():
    names = [
        p["name"] for p in client.get("/api/products", params={"q": "shea"}).json()
    ]
    assert "Whipped Shea Curl Cream" in names


def test_products_by_ids_preserves_order_and_skips_unknown():
    ids = ["halo-jojoba-shine-oil", "nope", "coilwell-aloe-slip-leave-in"]
    got = [p["id"] for p in client.get("/api/products", params={"ids": ids}).json()]
    assert got == ["halo-jojoba-shine-oil", "coilwell-aloe-slip-leave-in"]


def test_product_detail_keeps_label_order():
    pid = "coilwell-whipped-shea-curl-cream"
    body = client.get(f"/api/products/{pid}").json()
    got = [line["ingredient"]["id"] for line in body["formula"]]
    assert got == [e.ingredient_id for e in catalog.get(pid).formula]
    assert got[:3] == ["water", "shea", "aloe"]
    assert body["price_from"] == min(l["price_usd"] for l in body["listings"])


def test_unknown_product_is_404():
    assert client.get("/api/products/does-not-exist").status_code == 404
    assert client.get("/api/products/does-not-exist/similar").status_code == 404


def test_similar_products_rank_by_formula_and_report_shared_ingredients():
    body = client.get("/api/products/coilwell-whipped-shea-curl-cream/similar").json()
    assert body
    assert all(r["product"]["id"] != "coilwell-whipped-shea-curl-cream" for r in body)
    sims = [r["similarity"] for r in body]
    assert sims == sorted(sims, reverse=True)
    # Ranked by formula, not category: other kinds of product can match.
    assert {r["product"]["category"] for r in body} - {"Curl cream"}
    # Every card shows a price.
    assert all(r["product"]["price_from"] is not None for r in body)
    # Water is a base ingredient; it would otherwise dominate every comparison.
    assert all(s["ingredient_id"] != "water" for r in body for s in r["shared"])
    # Shared ingredients follow this product's label.
    label = [
        e.ingredient_id for e in catalog.get("coilwell-whipped-shea-curl-cream").formula
    ]
    for r in body:
        ids = [s["ingredient_id"] for s in r["shared"]]
        assert ids == [i for i in label if i in ids]


def test_recommendations_only_return_matching_hair_types():
    body = client.post("/api/recommendations", json={"hair_types": ["4C"]}).json()
    assert body["results"]
    for r in body["results"]:
        assert "4C" in r["product"]["hair_types"]
        assert r["reasons"]


def test_recommendations_filter_by_query():
    body = client.post(
        "/api/recommendations", json={"hair_types": ["4B"], "query": "edges"}
    ).json()
    ids = [r["product"]["id"] for r in body["results"]]
    assert ids and ids[0] == "baobab-castor-edge-control"


def test_recommendations_skip_products_the_person_already_has():
    owned = ["coilwell-aloe-slip-leave-in"]
    body = client.post(
        "/api/recommendations",
        json={
            "hair_types": ["4A"],
            "liked_product_ids": owned,
            "current_product_ids": ["halo-jojoba-shine-oil"],
        },
    ).json()
    ids = {r["product"]["id"] for r in body["results"]}
    assert "coilwell-aloe-slip-leave-in" not in ids
    assert "halo-jojoba-shine-oil" not in ids


def test_recommendations_with_no_inputs_return_catalog():
    body = client.post("/api/recommendations", json={}).json()
    assert len(body["results"]) == min(24, len(catalog.products))
    assert body["total"] == len(catalog.products)


def test_a_bigger_limit_extends_the_same_ranking():
    def ids(limit):
        body = client.post("/api/recommendations", json={"limit": limit}).json()
        return [r["product"]["id"] for r in body["results"]]

    first, more = ids(5), ids(10)
    assert more[:5] == first
    assert len(more) == 10


# --- recommender hand-off ------------------------------------------------------


class FixedRecommender:
    """Proves a different Recommender can be swapped in without touching routes."""

    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> Ranking:
        p = catalog.summary(catalog.get("halo-jojoba-shine-oil"))
        band = environment.dew_point_band if environment else "none"
        return Ranking(
            [
                Recommendation(
                    product=p, score=1.0, reasons=[f"echo:{request.query}:{band}"]
                )
            ],
            1,
        )

    def similar_products(self, product_id: str, limit: int) -> list[SimilarProduct]:
        return []


@pytest.fixture
def fixed_recommender():
    app.dependency_overrides[get_recommender] = FixedRecommender
    yield
    app.dependency_overrides.pop(get_recommender)


def test_recommender_can_be_overridden(fixed_recommender):
    body = client.post(
        "/api/recommendations",
        json={"query": "hello", "location": PHILLY.model_dump()},
    ).json()
    assert body["results"][0]["reasons"] == ["echo:hello:humid"]
    assert client.get("/api/products/halo-jojoba-shine-oil/similar").json() == []


# --- location and environment --------------------------------------------------


def test_detect_location_uses_public_forwarded_ip(no_network):
    locations, _ = no_network
    body = client.get("/api/location", headers={"x-forwarded-for": "8.8.8.8, 10.0.0.1"})
    assert body.json()["label"] == "Philadelphia, Pennsylvania"
    assert locations.ips == ["8.8.8.8"]


def test_detect_location_from_local_dev_resolves_own_ip(no_network):
    locations, _ = no_network
    client.get("/api/location")
    # TestClient's host isn't a public IP, same as 127.0.0.1 behind the Vite proxy.
    assert locations.ips == [None]


@pytest.mark.parametrize(
    "forwarded, host, expected",
    [
        ("8.8.8.8", "127.0.0.1", "8.8.8.8"),
        (None, "1.1.1.1", "1.1.1.1"),
        ("10.0.0.5", "127.0.0.1", None),
        ("not-an-ip", "192.168.1.4", None),
        (None, "::1", None),
    ],
)
def test_client_ip(forwarded, host, expected):
    class Req:
        headers = {"x-forwarded-for": forwarded} if forwarded else {}
        client = type("C", (), {"host": host})()

    assert client_ip(Req()) == expected


def test_search_locations():
    body = client.get("/api/locations", params={"q": "phila"}).json()
    assert body[0]["source"] == "manual"
    assert client.get("/api/locations").json() == []


def test_recommendations_without_location_skip_weather(no_network):
    _, environment = no_network
    body = client.post("/api/recommendations", json={"hair_types": ["4C"]}).json()
    assert body["environment"] is None
    assert environment.calls == []


def test_humid_weather_nudges_frizz_fighters_up(no_network):
    _, environment = no_network
    request = {"hair_types": ["3B"], "location": PHILLY.model_dump()}
    environment.dew_point_c = 20
    humid = client.post("/api/recommendations", json=request).json()
    assert humid["environment"]["dew_point_band"] == "humid"
    gel = next(
        r
        for r in humid["results"]
        if r["product"]["id"] == "baobab-flaxseed-defining-gel"
    )
    assert (
        "Flaxseed extract and castor oil fight frizz for today's humid air"
        in gel["reasons"]
    )
    assert (
        "Aloe vera juice and glycerin can cause frizz in today's humid air"
        in gel["warnings"]
    )
    assert environment.calls == [(39.95, -75.16)]


def test_dry_weather_nudges_moisture_up(no_network):
    _, environment = no_network
    environment.dew_point_c = -5
    body = client.post(
        "/api/recommendations",
        json={"hair_types": ["4C"], "location": PHILLY.model_dump()},
    ).json()
    assert body["environment"]["dew_point_band"] == "dry"
    reasons = [reason for r in body["results"] for reason in r["reasons"]]
    assert (
        "Mango butter and shea butter lock moisture in and add moisture for today's dry air"
        in reasons
    )


@pytest.mark.parametrize(
    "dew_point_c, band",
    [
        (-10, "dry"),
        (3.9, "dry"),
        (4, "comfortable"),
        (16, "comfortable"),
        (16.1, "humid"),
    ],
)
def test_dew_point_band(dew_point_c, band):
    assert dew_point_band(dew_point_c) == band


# --- real providers against canned upstream responses ---------------------------
# Shapes copied from live responses of ipwho.is and Open-Meteo.


def mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ipwhois_response_parses_to_location():
    seen = []

    def handler(req: httpx.Request):
        seen.append(str(req.url))
        return httpx.Response(
            200,
            json={
                "success": True,
                "city": "Huntington",
                "region": "West Virginia",
                "country_code": "US",
                "latitude": 38.42,
                "longitude": -82.44,
            },
        )

    loc = PublicLocationService(mock_client(handler)).from_ip("8.8.8.8")
    assert loc.label == "Huntington, West Virginia"
    assert loc.source == "ip"
    assert seen == ["https://ipwho.is/8.8.8.8"]


def test_failed_ip_lookup_returns_none_and_is_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, json={"success": False, "message": "rate limited"})

    service = PublicLocationService(mock_client(handler))
    assert service.from_ip(None) is None
    assert service.from_ip(None) is None
    assert len(calls) == 2


def test_open_meteo_geocoding_parses_to_locations():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Philadelphia",
                        "admin1": "Pennsylvania",
                        "country_code": "US",
                        "latitude": 39.95,
                        "longitude": -75.16,
                    }
                ]
            },
        )

    [loc] = PublicLocationService(mock_client(handler)).search("Philadelphia")
    assert loc.label == "Philadelphia, Pennsylvania"
    assert loc.source == "manual"


def test_open_meteo_weather_parses_to_environment():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 19.8,
                    "relative_humidity_2m": 34,
                    "dew_point_2m": 3.5,
                    "uv_index": 4.35,
                }
            },
        )

    env = OpenMeteoEnvironment(mock_client(handler)).current(39.95, -75.16)
    assert env.dew_point_band == "dry"
    assert env.relative_humidity_pct == 34
    assert env.advice
