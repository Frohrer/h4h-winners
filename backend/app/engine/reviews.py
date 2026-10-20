"""Real-world evidence from reviews (data/reviews.jsonl, written by the review pipeline).

A review from someone with the same hair type counts fully. Neighbouring types count
less ("3C liked it" says something about 4A; people often misjudge their type by a
step). Reviews that don't say a hair type count a little.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.engine.vocab import HAIR_TYPES, HELPS, Need

log = logging.getLogger(__name__)

REVIEWS_PATH = Path(__file__).parent.parent / "data" / "reviews.jsonl"

NO_TYPE_WEIGHT = 0.1
STEP_PENALTY = 0.35
# With this much matching evidence the reviews count half; fewer and they barely count.
HALF_TRUST_AT = 5


class ReviewSignal(BaseModel):
    """One review that mentions the writer's hair: one JSON object per line."""

    product_id: str
    hair_type: str | None = None
    porosity: Literal["low", "medium", "high"] | None = None
    thickness: Literal["fine", "medium", "coarse"] | None = None
    sentiment: float = Field(ge=-1, le=1)
    helped: list[Need] = Field(default_factory=list)
    hurt: list[Need] = Field(default_factory=list)
    climate: str | None = None
    quote: str | None = Field(default=None, max_length=300)
    source_url: str | None = None


@dataclass(frozen=True)
class Evidence:
    total: int  # reviews of this product, any hair type
    same_type: int  # reviews from people with one of the asker's hair types
    score: float  # -1..1, shrunk toward 0 when the evidence is thin
    summary: str | None


def _closeness(
    review: ReviewSignal, hair_types: list[str], porosity: str | None
) -> float:
    if not review.hair_type or review.hair_type not in HAIR_TYPES or not hair_types:
        w = NO_TYPE_WEIGHT
    else:
        r = HAIR_TYPES.index(review.hair_type)
        steps = min(abs(r - HAIR_TYPES.index(t)) for t in hair_types)
        w = max(0.0, 1 - STEP_PENALTY * steps)
    if review.porosity and porosity and w > 0:
        w *= 1.25 if review.porosity == porosity else 0.75
    return w


class ReviewIndex:
    def __init__(self, signals: list[ReviewSignal]):
        self.by_product: dict[str, list[ReviewSignal]] = {}
        for s in signals:
            self.by_product.setdefault(s.product_id, []).append(s)

    def evidence(
        self, product_id: str, hair_types: list[str], porosity: str | None = None
    ) -> Evidence | None:
        reviews = self.by_product.get(product_id)
        if not reviews:
            return None
        hair_types = [t for t in hair_types if t in HAIR_TYPES]
        same = [r for r in reviews if r.hair_type in hair_types]

        weight = weighted = 0.0
        helped: dict[str, float] = {}
        for r in reviews:
            w = _closeness(r, hair_types, porosity)
            weight += w
            weighted += w * r.sentiment
            for need in r.helped:
                helped[need] = helped.get(need, 0) + w
        if weight == 0:
            return Evidence(len(reviews), len(same), 0.0, None)

        trust = weight / (weight + HALF_TRUST_AT)
        summary = None
        if same:
            liked = sum(1 for r in same if r.sentiment > 0)
            summary = f"{liked} of {len(same)} reviewers with {'/'.join(hair_types)} hair liked it"
            if helped:
                top = max(helped, key=helped.get)
                summary += f": it {HELPS[top]}"
        return Evidence(len(reviews), len(same), weighted / weight * trust, summary)


def load_reviews(path: Path = REVIEWS_PATH) -> ReviewIndex:
    """Bad lines are skipped and counted, so one broken row never takes the API down."""
    if not path.exists():
        return ReviewIndex([])
    signals, skipped = [], 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            signals.append(ReviewSignal.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            skipped += 1
    log.info("Loaded %d review signals (%d bad lines skipped)", len(signals), skipped)
    return ReviewIndex(signals)
