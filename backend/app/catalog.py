"""In-memory product catalog loaded from a JSON file.

The app loads the catalog built from scraped data (scripts/build_catalog.py,
path in STRAND_CATALOG) when it exists, else the fictional seed. The routes and
the recommender only talk to Catalog.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from app.models import (
    FormulaLine,
    HairType,
    Ingredient,
    Product,
    ProductDetail,
    ProductSummary,
)

SEED_PATH = Path(__file__).parent / "data" / "catalog.json"


class CatalogFile(BaseModel):
    hair_types: list[HairType]
    ingredients: list[Ingredient]
    products: list[Product]


class Catalog:
    def __init__(self, data: CatalogFile):
        self.hair_types = data.hair_types
        self.ingredients = {i.id: i for i in data.ingredients}
        self.products = {p.id: p for p in data.products}

    def get(self, product_id: str) -> Product | None:
        return self.products.get(product_id)

    def search(self, q: str, limit: int = 8) -> list[Product]:
        """Name/brand lookup for the "products you like" picker, not ranking."""
        needle = q.strip().lower()
        if not needle:
            return list(self.products.values())[:limit]
        hits = [
            p
            for p in self.products.values()
            if needle in p.name.lower() or needle in p.brand.lower()
        ]
        return hits[:limit]

    def summary(self, product: Product) -> ProductSummary:
        prices = [listing.price_usd for listing in product.listings]
        return ProductSummary(
            id=product.id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            hair_types=product.hair_types,
            tags=product.tags,
            color=product.color,
            image_url=product.image_url,
            price_from=min(prices) if prices else None,
        )

    def detail(self, product: Product) -> ProductDetail:
        lines = [
            FormulaLine(ingredient=self.ingredients[entry.ingredient_id])
            for entry in product.formula
        ]
        return ProductDetail(
            **self.summary(product).model_dump(),
            description=product.description,
            listings=sorted(product.listings, key=lambda listing: listing.price_usd),
            formula=lines,
        )


def load_catalog(path: Path = SEED_PATH) -> Catalog:
    data = CatalogFile.model_validate(json.loads(path.read_text()))
    return Catalog(data)


@lru_cache
def get_catalog() -> Catalog:
    built = Path(os.environ.get("STRAND_CATALOG", ""))
    return load_catalog(built if built.is_file() else SEED_PATH)
