"""Recommender interface and a placeholder implementation.

The real recommendation system plugs in by implementing `Recommender` and
returning it from get_recommender() (or via app.dependency_overrides in tests).
Nothing else in the app needs to change: routes call only these three methods.

StubRecommender is deliberately naive (keyword prefix matching, weighted
ingredient overlap) so the UI has believable results to render. Don't tune it;
replace it.
"""

import re
from functools import lru_cache
from typing import Protocol

from app.catalog import Catalog, get_catalog
from app.models import (
    DewPointBand,
    Environment,
    Product,
    Recommendation,
    RecommendationRequest,
    SharedIngredient,
    SimilarFormula,
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

    def similar_formulas(self, product_id: str, limit: int) -> list[SimilarFormula]:
        """Products whose ingredient blend and concentrations are closest, any category."""
        ...

    def similar_products(self, product_id: str, limit: int) -> list[Recommendation]:
        """Alternatives to a product: same job, same hair types, related formula."""
        ...


# fmt: off
STOPWORDS = {
    "a", "an", "and", "for", "i", "in", "is", "it", "my", "of", "on", "or",
    "that", "the", "to", "want", "with", "without", "need", "something", "looking",
    # Substring matching makes these hit nearly every description.
    "less", "more", "very", "too", "really", "help", "helps", "make", "makes",
    "good", "best", "hair", "product", "products", "keep", "stay", "get",
}
# fmt: on


CLIMATE_TAGS: dict[DewPointBand, tuple[set[str], str]] = {
    "humid": ({"hold", "frizz", "definition"}, "Fights frizz in humid air"),
    "dry": ({"moisture", "sealing", "dryness"}, "Extra moisture for dry air"),
}


def _stem(word: str) -> str:
    # A 5-char prefix makes "moisturizing" hit "moisture" and "defining" hit
    # "definition" without pulling in a stemming library for throwaway code.
    return word[:5] if len(word) > 5 else word.rstrip("s")


def _tokens(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", text.lower())
        if w not in STOPWORDS and len(w) > 2
    ]


class StubRecommender:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

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

    def similar_formulas(self, product_id: str, limit: int) -> list[SimilarFormula]:
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
            SimilarFormula(
                product=self.catalog.summary(other),
                similarity=round(sim, 3),
                shared=self._shared(target, other),
            )
            for sim, other in scored[:limit]
        ]

    # --- product-to-product -----------------------------------------------------

    def similar_products(self, product_id: str, limit: int) -> list[Recommendation]:
        target = self.catalog.get(product_id)
        if target is None:
            return []
        target_types = set(target.hair_types)
        results = []
        for other in self.catalog.products.values():
            if other.id == target.id:
                continue
            same_category = other.category == target.category
            shared_types = target_types & set(other.hair_types)
            type_overlap = len(shared_types) / len(target_types | set(other.hair_types))
            formula = self._formula_similarity(target, other)
            # Category dominates so this section reads as "alternatives to this
            # product"; ingredient-driven matches have their own section.
            score = 0.45 * same_category + 0.3 * type_overlap + 0.25 * formula
            if score <= 0.2:
                continue
            reasons = []
            if same_category:
                reasons.append(f"Also a {target.category.lower()}")
            if shared_types:
                reasons.append(f"Made for {', '.join(sorted(shared_types))}")
            results.append(
                Recommendation(
                    product=self.catalog.summary(other),
                    score=round(score, 3),
                    reasons=reasons,
                )
            )
        results.sort(key=lambda r: -r.score)
        return results[:limit]

    # --- personalized search ----------------------------------------------------

    def _searchable_text(self, product: Product) -> str:
        ingredient_text = " ".join(
            f"{self.catalog.ingredients[e.ingredient_id].name} {self.catalog.ingredients[e.ingredient_id].function}"
            for e in product.formula
        )
        return " ".join(
            [
                product.name,
                product.brand,
                product.category,
                product.description,
                " ".join(product.tags),
                ingredient_text,
            ]
        ).lower()

    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> list[Recommendation]:
        wanted_types = set(request.hair_types)
        owned_ids = set(request.liked_product_ids) | set(request.current_product_ids)
        owned = [p for pid in owned_ids if (p := self.catalog.get(pid))]
        query_words = _tokens(request.query)
        climate = CLIMATE_TAGS.get(environment.dew_point_band) if environment else None

        results = []
        for product in self.catalog.products.values():
            # People already have these; suggesting them back is noise.
            if product.id in owned_ids:
                continue

            reasons = []
            score = 0.0

            if wanted_types:
                matched_types = wanted_types & set(product.hair_types)
                if not matched_types:
                    continue
                score += 3 * len(matched_types) / len(wanted_types)
                reasons.append(f"Made for {', '.join(sorted(matched_types))}")

            if query_words:
                text = self._searchable_text(product)
                hits = [w for w in query_words if _stem(w) in text]
                if not hits:
                    continue
                score += 4 * len(hits) / len(query_words)
                reasons.append("Matches " + ", ".join(f"“{w}”" for w in hits))

            if owned:
                best = max(owned, key=lambda o: self._formula_similarity(product, o))
                best_sim = self._formula_similarity(product, best)
                if best_sim > 0.15:
                    score += 2 * best_sim
                    reasons.append(f"Similar formula to {best.name}")

            # A nudge, not a filter: weather changes daily and shouldn't hide
            # products that otherwise fit.
            if climate and climate[0] & set(product.tags):
                score += 1
                reasons.append(climate[1])

            results.append(
                Recommendation(
                    product=self.catalog.summary(product),
                    score=round(score, 3),
                    reasons=reasons,
                )
            )

        results.sort(key=lambda r: -r.score)
        return results[: request.limit]


@lru_cache
def get_recommender() -> Recommender:
    return StubRecommender(get_catalog())
