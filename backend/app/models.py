"""Catalog and API models.

These are the contract between three parties: the scraper (writes catalog
records), the recommender (reads them, returns ranked results), and the
frontend (mirrors the response shapes in frontend/src/types.ts — keep the two
in sync by hand until we generate TS types from /openapi.json).
"""

from typing import Literal

from pydantic import BaseModel, Field

HairFamily = Literal["Straight", "Wavy", "Curly", "Coily"]


class HairType(BaseModel):
    code: str  # Andre Walker system: "1A" .. "4C"
    family: HairFamily
    description: str


# --- Catalog records (what the scraper will produce) -------------------------


class Ingredient(BaseModel):
    id: str
    name: str
    inci: str
    function: str
    what_it_does: str
    why_its_added: str
    # Water and similar carriers are in nearly every formula at 50-80%, so
    # counting them makes every product look alike. Similarity skips these.
    is_base: bool = False


class FormulaEntry(BaseModel):
    ingredient_id: str
    # Brands almost never publish concentrations; scraped values will be
    # estimates from INCI order, and some will be missing entirely.
    concentration_pct: float | None = None


class Listing(BaseModel):
    retailer: str
    price_usd: float
    size: str
    url: str


class Product(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    description: str
    hair_types: list[str]
    tags: list[str] = Field(default_factory=list)
    # Placeholder tint for the generated packaging illustration until
    # scraped product photos land in image_url.
    color: str
    image_url: str | None = None
    formula: list[FormulaEntry]
    listings: list[Listing]


# --- Location and environment --------------------------------------------------


class Location(BaseModel):
    label: str  # "Philadelphia, Pennsylvania"
    city: str | None = None
    region: str | None = None
    country_code: str | None = None
    latitude: float
    longitude: float
    # "ip" = detected from the connection (approximate, often off by a city
    # or two on mobile networks and VPNs); "manual" = chosen by the person.
    source: Literal["ip", "manual"]


DewPointBand = Literal["dry", "comfortable", "humid"]


class Environment(BaseModel):
    temperature_c: float
    relative_humidity_pct: float
    dew_point_c: float
    uv_index: float | None = None
    # Dew point, not relative humidity, decides whether humectants like
    # glycerin pull water into hair (humid) or out of it (dry). It's the
    # climate signal curly-hair routines are usually tuned around.
    dew_point_band: DewPointBand
    advice: str


# --- API responses ------------------------------------------------------------


class ProductSummary(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    hair_types: list[str]
    tags: list[str]
    color: str
    image_url: str | None
    price_from: float | None


class FormulaLine(BaseModel):
    ingredient: Ingredient
    concentration_pct: float | None


class ProductDetail(ProductSummary):
    description: str
    listings: list[Listing]
    formula: list[FormulaLine]


class SharedIngredient(BaseModel):
    ingredient_id: str
    name: str
    this_pct: float | None
    other_pct: float | None


class SimilarProduct(BaseModel):
    product: ProductSummary
    similarity: float  # 0..1, shown to people as "% formula match"
    shared: list[SharedIngredient]  # most-shared first


class Recommendation(BaseModel):
    product: ProductSummary
    score: float
    # Short, user-facing explanations ("Made for 4A, 4B"). The real
    # recommender should keep filling these — the UI shows them under each
    # result so people can tell why something was suggested.
    reasons: list[str]
    # Things to watch out for ("Glycerin can cause frizz in today's humid air").
    warnings: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    hair_types: list[str] = Field(default_factory=list)
    liked_product_ids: list[str] = Field(default_factory=list)
    current_product_ids: list[str] = Field(default_factory=list)
    query: str = ""
    # Optional hair details; each sharpens the match when the UI starts asking for it.
    porosity: Literal["low", "medium", "high"] | None = None
    thickness: Literal["fine", "medium", "coarse"] | None = None
    density: Literal["low", "medium", "high"] | None = None
    scalp: Literal["normal", "oily", "dry", "flaky"] | None = None
    color_treated: bool = False
    # None means the person turned location off; recommend without climate.
    location: Location | None = None
    limit: int = Field(default=24, ge=1, le=1000)


class RecommendationResponse(BaseModel):
    results: list[Recommendation]
    # How many products matched in all; results holds the top `limit` of them.
    total: int
    # Echoed so the UI can say which conditions shaped the results.
    environment: Environment | None = None
