"""Recommender interface and the needs-graph implementation.

Routes call only the two Recommender methods, so another implementation can be
swapped in via get_recommender() (or app.dependency_overrides in tests).

GraphRecommender walks: hair + search + weather → needs → ingredient groups →
products, then adds what reviews from people with similar hair say. The hair
knowledge lives in app/engine/rules.py and app/engine/ingredient_groups.py.
"""

import re
from functools import lru_cache
from typing import Protocol

from app.catalog import Catalog, get_catalog
from app.engine import query
from app.engine.needs import needs_for
from app.engine.reviews import ReviewIndex, load_reviews
from app.engine.scoring import Line, analyze, explain, score
from app.engine.vocab import Condition
from app.models import (
    Environment,
    Product,
    Recommendation,
    RecommendationRequest,
    SharedIngredient,
    SimilarProduct,
)


class Recommender(Protocol):
    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> list[Recommendation]:
        """Rank products for a person's hair types, liked/current products, free-text query,
        and current conditions where they are (None if location is off or the lookup failed).
        request.location is still available for anything beyond current weather,
        e.g. regional water hardness."""
        ...

    def similar_products(self, product_id: str, limit: int) -> list[SimilarProduct]:
        """Products whose ingredient blend and concentrations are closest, any category.

        "Similar" means similar formula on purpose. An earlier version also had
        a category-first "alternatives" list; showing both on one page read as
        two overlapping lists with no clear difference, so they were merged.
        """
        ...


# How much each signal moves the score. Ingredient scores of good matches usually sit
# between 0.2 and 1, so these are sized to nudge, not to override, that ranking.
REVIEW_WEIGHT = 0.5  # dozens of same-type reviews can beat a moderate ingredient gap
MADE_FOR_WEIGHT = 0.2  # the brand says it's for your hair type
SEARCH_HIT_WEIGHT = 1.0  # the words you typed appear on the product
SIMILAR_TO_LIKED_WEIGHT = 1.0
SIMILAR_TO_LIKED_MIN = 0.15
MAX_REASONS = 4

# Very humid starts here; the API's own bands only say "humid" above 16 °C.
VERY_HUMID_FROM_C = 21.0
STRONG_SUN_UV = 6.0
COLD_BELOW_C = 5.0

# fmt: off
STOPWORDS = {
    "a", "an", "and", "for", "i", "in", "is", "it", "my", "of", "on", "or",
    "that", "the", "to", "want", "with", "without", "need", "something", "looking",
    # Substring matching makes these hit nearly every description.
    "less", "more", "very", "too", "really", "help", "helps", "make", "makes",
    "good", "best", "hair", "product", "products", "keep", "stay", "get",
    "today", "tonight", "going",
}
# fmt: on


def _stem(word: str) -> str:
    # A 5-char prefix makes "moisturizing" hit "moisture" and "defining" hit "definition".
    return word[:5] if len(word) > 5 else word.rstrip("s")


def _tokens(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", text.lower())
        if w not in STOPWORDS and len(w) > 2
    ]


def conditions_from(environment: Environment | None) -> list[Condition]:
    if environment is None:
        return []
    out: list[Condition] = []
    if environment.dew_point_band == "dry":
        out.append("very_dry_air")
    elif environment.dew_point_band == "humid":
        out.append(
            "very_humid" if environment.dew_point_c >= VERY_HUMID_FROM_C else "humid"
        )
    if (environment.uv_index or 0) >= STRONG_SUN_UV:
        out.append("strong_sun")
    if environment.temperature_c < COLD_BELOW_C:
        out.append("cold")
    return out


class GraphRecommender:
    def __init__(self, catalog: Catalog, reviews: ReviewIndex):
        self.catalog = catalog
        self.reviews = reviews
        self.lines: dict[str, list[Line]] = {
            p.id: analyze(
                (
                    catalog.ingredients[e.ingredient_id].name,
                    catalog.ingredients[e.ingredient_id].inci,
                    e.concentration_pct,
                )
                for e in p.formula
            )
            for p in catalog.products.values()
        }
        self.kinds = {
            p.id: query.kind_of(f"{p.category} {p.name}")
            for p in catalog.products.values()
        }

    # --- formula similarity ---------------------------------------------------

    def _weights(self, product: Product) -> dict[str, float]:
        weights = {}
        for entry in product.formula:
            if self.catalog.ingredients[entry.ingredient_id].is_base:
                continue
            # Missing concentrations count as a trace amount so presence still matters.
            weights[entry.ingredient_id] = entry.concentration_pct or 0.5
        return weights

    def _formula_similarity(self, a: Product, b: Product) -> float:
        # Weighted Jaccard: shared ingredients count by the smaller of the two
        # concentrations, so 12% shea vs 1% shea is a weak match, not a strong one.
        wa, wb = self._weights(a), self._weights(b)
        keys = wa.keys() | wb.keys()
        if not keys:
            return 0.0
        overlap = sum(min(wa.get(k, 0), wb.get(k, 0)) for k in keys)
        union = sum(max(wa.get(k, 0), wb.get(k, 0)) for k in keys)
        return overlap / union

    def _shared(self, a: Product, b: Product) -> list[SharedIngredient]:
        wa, wb = self._weights(a), self._weights(b)
        conc_a = {e.ingredient_id: e.concentration_pct for e in a.formula}
        conc_b = {e.ingredient_id: e.concentration_pct for e in b.formula}
        shared = sorted(wa.keys() & wb.keys(), key=lambda k: -min(wa[k], wb[k]))
        return [
            SharedIngredient(
                ingredient_id=k,
                name=self.catalog.ingredients[k].name,
                this_pct=conc_a[k],
                other_pct=conc_b[k],
            )
            for k in shared
        ]

    def similar_products(self, product_id: str, limit: int) -> list[SimilarProduct]:
        target = self.catalog.get(product_id)
        if target is None:
            return []
        scored = [
            (self._formula_similarity(target, other), other)
            for other in self.catalog.products.values()
            if other.id != target.id
        ]
        scored = [s for s in scored if s[0] > 0]
        scored.sort(key=lambda s: -s[0])
        return [
            SimilarProduct(
                product=self.catalog.summary(other),
                similarity=round(sim, 3),
                shared=self._shared(target, other),
            )
            for sim, other in scored[:limit]
        ]

    # --- personalized ranking -----------------------------------------------------

    def _searchable_text(self, product: Product) -> str:
        return " ".join(
            [
                product.name,
                product.brand,
                product.category,
                product.description,
                " ".join(product.tags),
            ]
        ).lower()

    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> list[Recommendation]:
        wanted_types = set(request.hair_types)
        owned_ids = set(request.liked_product_ids) | set(request.current_product_ids)
        liked = [p for pid in request.liked_product_ids if (p := self.catalog.get(pid))]
        wanted_kinds = query.kinds_in(request.query)
        words = _tokens(request.query)

        # Weather where they are, plus any climate they mention ("beach trip").
        conditions = conditions_from(environment)
        conditions += [
            c for c in query.climates_in(request.query) if c not in conditions
        ]
        needs = needs_for(
            request.hair_types,
            porosity=request.porosity,
            thickness=request.thickness,
            density=request.density,
            scalp=request.scalp,
            color_treated=request.color_treated,
            goals=query.goals_in(request.query),
            conditions=conditions,
        )

        results = []
        for product in self.catalog.products.values():
            # People already have these; suggesting them back is noise.
            if product.id in owned_ids:
                continue
            if wanted_kinds and self.kinds[product.id] not in wanted_kinds:
                continue
            made_for = wanted_types & set(product.hair_types)
            # A product made for other hair types is out; one that doesn't say is judged on ingredients.
            if wanted_types and product.hair_types and not made_for:
                continue

            total, contributions = score(self.lines[product.id], needs, conditions)
            ingredient_reasons, warnings = explain(contributions, needs)
            # Short, direct signals first; ingredient reasons fill the remaining slots.
            reasons = []

            if made_for:
                total += MADE_FOR_WEIGHT * len(made_for) / len(wanted_types)
                reasons.append(f"Made for {', '.join(sorted(made_for))}")

            evidence = self.reviews.evidence(
                product.id, request.hair_types, request.porosity
            )
            if evidence:
                total += REVIEW_WEIGHT * evidence.score
                if evidence.summary:
                    reasons.append(evidence.summary)

            if words:
                text = self._searchable_text(product)
                hits = [w for w in words if _stem(w) in text]
                if hits:
                    total += SEARCH_HIT_WEIGHT * len(hits) / len(words)
                    reasons.append("Matches " + ", ".join(f"“{w}”" for w in hits))

            if liked:
                best = max(liked, key=lambda o: self._formula_similarity(product, o))
                sim = self._formula_similarity(product, best)
                if sim > SIMILAR_TO_LIKED_MIN:
                    total += SIMILAR_TO_LIKED_WEIGHT * sim
                    reasons.append(f"Similar formula to {best.name}")

            reasons += ingredient_reasons

            results.append(
                Recommendation(
                    product=self.catalog.summary(product),
                    score=round(total, 3),
                    reasons=reasons[:MAX_REASONS],
                    warnings=warnings,
                )
            )

        results.sort(key=lambda r: -r.score)
        return results[: request.limit]


@lru_cache
def get_recommender() -> Recommender:
    return GraphRecommender(get_catalog(), load_reviews())
