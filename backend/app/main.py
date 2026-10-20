from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from app.catalog import Catalog, get_catalog
from app.environment import EnvironmentProvider, get_environment_provider
from app.location import LocationService, client_ip, get_location_service
from app.models import (
    HairType,
    Location,
    ProductDetail,
    ProductSummary,
    RecommendationRequest,
    RecommendationResponse,
    SimilarProduct,
)
from app.recommender import Recommender, get_recommender

app = FastAPI(title="strands.hair API")

CatalogDep = Annotated[Catalog, Depends(get_catalog)]
RecommenderDep = Annotated[Recommender, Depends(get_recommender)]
LocationDep = Annotated[LocationService, Depends(get_location_service)]
EnvironmentDep = Annotated[EnvironmentProvider, Depends(get_environment_provider)]


def _product_or_404(catalog: Catalog, product_id: str):
    product = catalog.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=404, detail=f"No product with id '{product_id}'"
        )
    return product


@app.get("/api/hair-types")
def hair_types(catalog: CatalogDep) -> list[HairType]:
    return catalog.hair_types


@app.get("/api/products")
def list_products(
    catalog: CatalogDep,
    q: str = "",
    ids: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=8, ge=1, le=100),
) -> list[ProductSummary]:
    # ?ids= resolves the browser-stored favorites/using lists in one call.
    if ids:
        products = [p for pid in ids if (p := catalog.get(pid))]
    else:
        products = catalog.search(q, limit)
    return [catalog.summary(p) for p in products]


@app.get("/api/products/{product_id}")
def product_detail(product_id: str, catalog: CatalogDep) -> ProductDetail:
    return catalog.detail(_product_or_404(catalog, product_id))


@app.get("/api/products/{product_id}/similar")
def similar_products(
    product_id: str,
    catalog: CatalogDep,
    recommender: RecommenderDep,
    limit: int = Query(default=6, ge=1, le=20),
) -> list[SimilarProduct]:
    _product_or_404(catalog, product_id)
    return recommender.similar_products(product_id, limit)


@app.post("/api/recommendations")
def recommendations(
    body: RecommendationRequest,
    recommender: RecommenderDep,
    environments: EnvironmentDep,
) -> RecommendationResponse:
    # Weather is looked up here rather than inside the recommender so every
    # implementation gets the same environment and the UI can show what was used.
    environment = (
        environments.current(body.location.latitude, body.location.longitude)
        if body.location
        else None
    )
    return RecommendationResponse(
        results=recommender.recommend(body, environment),
        environment=environment,
    )


@app.get("/api/location")
def detect_location(request: Request, locations: LocationDep) -> Location | None:
    """Best guess from the visitor's IP. The UI calls this once and stores the
    result, so people can change or remove it without it being re-detected."""
    return locations.from_ip(client_ip(request))


@app.get("/api/locations")
def search_locations(locations: LocationDep, q: str = "") -> list[Location]:
    return locations.search(q)
