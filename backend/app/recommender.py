"""Recommender interface and the needs-graph implementation.

Routes call only the two Recommender methods, so another implementation can be
swapped in via get_recommender() (or app.dependency_overrides in tests).

GraphRecommender walks: hair + search + weather → needs → ingredient groups →
products, then adds what reviews from people with similar hair say. The hair
knowledge lives in app/engine/rules.py and app/engine/ingredient_groups.py.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import NamedTuple, Protocol

from app.catalog import Catalog, get_catalog
from app.engine import query
from app.engine.needs import Needs, needs_for
from app.engine.reviews import ReviewIndex, load_reviews
from app.engine.scoring import (
    Delivery,
    analyze,
    delivery,
    explain,
    position_weight,
    quick_score,
    score,
)
from app.engine.vocab import Condition
from app.models import (
    Environment,
    Product,
    Recommendation,
    RecommendationRequest,
    SharedIngredient,
    SimilarProduct,
)


class Ranking(NamedTuple):
    results: list[Recommendation]
    # Every eligible product, not just the request.limit that were explained.
    total: int


class Recommender(Protocol):
    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> Ranking:
        """Rank products for a person's hair types, liked/current products, free-text query,
        and current conditions where they are (None if location is off or the lookup failed).
        request.location is still available for anything beyond current weather,
        e.g. regional water hardness."""
        ...

    def similar_products(self, product_id: str, limit: int) -> list[SimilarProduct]:
        """Products whose ingredients and their label order are closest, any category.

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


@dataclass(frozen=True)
class _Ask:
    """What one request asks for, worked out once before ranking every product."""

    request: RecommendationRequest
    wanted_types: set[str]
    owned_ids: set[str]
    liked: list[Product]
    wanted_kinds: set[str]
    words: list[str]  # search words left after product kinds are taken out
    conditions: list[Condition]
    needs: Needs


class GraphRecommender:
    def __init__(self, catalog: Catalog, reviews: ReviewIndex):
        self.catalog = catalog
        self.reviews = reviews
        self.lines = {
            p.id: analyze(
                (
                    catalog.ingredients[e.ingredient_id].name,
                    catalog.ingredients[e.ingredient_id].inci,
                )
                for e in p.formula
            )
            for p in catalog.products.values()
        }
        self.deliveries: dict[str, Delivery] = {
            pid: delivery(lines) for pid, lines in self.lines.items()
        }
        self.kinds = {
            p.id: query.product_kind(p.name, p.category)
            for p in catalog.products.values()
        }
        self.formula_weights = {
            p.id: self._compute_weights(p) for p in catalog.products.values()
        }

    # --- formula similarity ---------------------------------------------------

    def _weights(self, product: Product) -> dict[str, float]:
        return self.formula_weights[product.id]

    def _compute_weights(self, product: Product) -> dict[str, float]:
        """Ingredient id -> weight by place on the label, in label order."""
        return {
            entry.ingredient_id: position_weight(i)
            for i, entry in enumerate(product.formula)
            if not self.catalog.ingredients[entry.ingredient_id].is_base
        }

    def _formula_similarity(self, a: Product, b: Product) -> float:
        # Weighted Jaccard: shared ingredients count by the lower of their two label
        # spots, so shea second on one label and last on another is a weak match.
        wa, wb = self._weights(a), self._weights(b)
        keys = wa.keys() | wb.keys()
        if not keys:
            return 0.0
        overlap = sum(min(wa.get(k, 0), wb.get(k, 0)) for k in keys)
        union = sum(max(wa.get(k, 0), wb.get(k, 0)) for k in keys)
        return overlap / union

    def _shared(self, a: Product, b: Product) -> list[SharedIngredient]:
        """Ingredients in both, in the order they appear on a's label."""
        wb = self._weights(b)
        return [
            SharedIngredient(ingredient_id=k, name=self.catalog.ingredients[k].name)
            for k in self._weights(a)
            if k in wb
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

    def _ask(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> _Ask:
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
        return _Ask(
            request=request,
            wanted_types=set(request.hair_types),
            owned_ids=set(request.liked_product_ids) | set(request.current_product_ids),
            liked=[
                p for pid in request.liked_product_ids if (p := self.catalog.get(pid))
            ],
            wanted_kinds=query.kinds_in(request.query),
            # Words that picked a product kind already did their job.
            words=_tokens(query.without_kinds(request.query)),
            conditions=conditions,
            needs=needs,
        )

    def _eligible(self, product: Product, ask: _Ask) -> bool:
        # People already have these; suggesting them back is noise.
        if product.id in ask.owned_ids:
            return False
        if ask.wanted_kinds and self.kinds[product.id] not in ask.wanted_kinds:
            return False
        # A product made for other hair types is out; one that doesn't say is judged on ingredients.
        made_for = ask.wanted_types & set(product.hair_types)
        return not (ask.wanted_types and product.hair_types and not made_for)

    # Each signal below returns (points to add, short reason or None).

    def _made_for_signal(self, product: Product, ask: _Ask) -> tuple[float, str | None]:
        made_for = ask.wanted_types & set(product.hair_types)
        if not made_for:
            return 0.0, None
        points = MADE_FOR_WEIGHT * len(made_for) / len(ask.wanted_types)
        return points, f"Made for {', '.join(sorted(made_for))}"

    def _review_signal(self, product: Product, ask: _Ask) -> tuple[float, str | None]:
        evidence = self.reviews.evidence(
            product.id, ask.request.hair_types, ask.request.porosity
        )
        if not evidence:
            return 0.0, None
        return REVIEW_WEIGHT * evidence.score, evidence.summary

    def _search_signal(self, product: Product, ask: _Ask) -> tuple[float, str | None]:
        if not ask.words:
            return 0.0, None
        text = self._searchable_text(product)
        hits = [w for w in ask.words if _stem(w) in text]
        if not hits:
            return 0.0, None
        points = SEARCH_HIT_WEIGHT * len(hits) / len(ask.words)
        return points, "Matches " + ", ".join(f"“{w}”" for w in hits)

    def _liked_signal(self, product: Product, ask: _Ask) -> tuple[float, str | None]:
        if not ask.liked:
            return 0.0, None
        best = max(ask.liked, key=lambda o: self._formula_similarity(product, o))
        sim = self._formula_similarity(product, best)
        if sim <= SIMILAR_TO_LIKED_MIN:
            return 0.0, None
        return SIMILAR_TO_LIKED_WEIGHT * sim, f"Similar formula to {best.name}"

    def _quick_rank(self, product: Product, ask: _Ask) -> tuple[float, list[str]]:
        total = quick_score(self.deliveries[product.id], ask.needs, ask.conditions)
        # Short, direct signals first; ingredient reasons fill the remaining slots.
        signals = []
        for points, signal in (
            self._made_for_signal(product, ask),
            self._review_signal(product, ask),
            self._search_signal(product, ask),
            self._liked_signal(product, ask),
        ):
            total += points
            if signal:
                signals.append(signal)
        return total, signals

    def _explained(
        self, total: float, product: Product, signals: list[str], ask: _Ask
    ) -> Recommendation:
        _, contributions = score(self.lines[product.id], ask.needs, ask.conditions)
        ingredient_reasons, warnings = explain(contributions, ask.needs)
        return Recommendation(
            product=self.catalog.summary(product),
            score=round(total, 3),
            reasons=(signals + ingredient_reasons)[:MAX_REASONS],
            warnings=warnings,
        )

    def recommend(
        self, request: RecommendationRequest, environment: Environment | None
    ) -> Ranking:
        ask = self._ask(request, environment)
        # Score everything cheaply, then explain only what will be shown.
        ranked = [
            (*self._quick_rank(product, ask), product)
            for product in self.catalog.products.values()
            if self._eligible(product, ask)
        ]
        ranked.sort(key=lambda r: -r[0])
        results = [
            self._explained(total, product, signals, ask)
            for total, signals, product in ranked[: request.limit]
        ]
        return Ranking(results, len(ranked))


@lru_cache
def get_recommender() -> Recommender:
    return GraphRecommender(get_catalog(), load_reviews())
