"""Real-world evidence from reviews (data/reviews.jsonl, written by the review pipeline).

A review from someone with the same hair type counts fully. Neighbouring types count
less ("3C liked it" says something about 4A; people often misjudge their type by a
step). Reviews that only name a hair family ("my curly hair") count moderately when
the asker is in that family. Reviews that don't say either count a little.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.engine.vocab import HAIR_TYPES, HELPS, Need, family_of
from app.models import HairFamily

log = logging.getLogger(__name__)

REVIEWS_PATH = Path(__file__).parent.parent / "data" / "reviews.jsonl"

NO_TYPE_WEIGHT = 0.1
# "Curly" spans 3A-3C, so a family-only review sits on average about one step from the
# asker's code (0.65 at STEP_PENALTY) but could be two (0.3); self-described families
# are also looser than codes (3C/4A reviewers say either curly or coily). 0.4 sits in
# between: four such reviews count about as much as one exact match.
FAMILY_WEIGHT = 0.4
STEP_PENALTY = 0.35
# With this much matching evidence the reviews count half; fewer and they barely count.
HALF_TRUST_AT = 5
# Fewer same-code reviewers than this are too few to quote ("1 of 4 liked it") when the
# asker's whole family has more to say.
QUOTE_SAME_TYPE_FROM = 10


class ReviewSignal(BaseModel):
    """One review that mentions the writer's hair: one JSON object per line."""

    product_id: str
    hair_type: str | None = None
    hair_family: HairFamily | None = None  # set alone when the review names no code
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


def _family(review: ReviewSignal) -> str | None:
    return review.hair_family or (review.hair_type and family_of(review.hair_type))


def _closeness(
    review: ReviewSignal, hair_types: list[str], porosity: str | None
) -> float:
    if review.hair_type in HAIR_TYPES and hair_types:
        r = HAIR_TYPES.index(review.hair_type)
        steps = min(abs(r - HAIR_TYPES.index(t)) for t in hair_types)
        w = max(0.0, 1 - STEP_PENALTY * steps)
    elif review.hair_family and review.hair_family in map(family_of, hair_types):
        w = FAMILY_WEIGHT
    else:
        w = NO_TYPE_WEIGHT
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
        # Same-code reviewers when there are enough, else everyone in the asker's
        # families ("3 of 4 reviewers with curly hair"), else no summary.
        summary = None
        families = list(dict.fromkeys(map(family_of, hair_types)))
        kin_family = [r for r in reviews if _family(r) in families]
        use_same = len(same) >= QUOTE_SAME_TYPE_FROM or len(same) >= len(kin_family)
        kin = same if use_same else kin_family
        if kin:
            liked = sum(1 for r in kin if r.sentiment > 0)
            who = "/".join(hair_types) if use_same else "/".join(families).lower()
            summary = f"{liked} of {len(kin)} reviewers with {who} hair liked it"
            if helped:
                top = max(helped, key=helped.get)
                summary += f": it {HELPS[top]}"
        return Evidence(len(reviews), len(same), weighted / weight * trust, summary)


def reviews_path() -> Path:
    """STRAND_REVIEWS (the generated file from scripts/build_reviews.py) when it exists."""
    env = os.environ.get("STRAND_REVIEWS")
    return Path(env) if env and Path(env).exists() else REVIEWS_PATH


def load_reviews(path: Path | None = None) -> ReviewIndex:
    """Bad lines are skipped and counted, so one broken row never takes the API down."""
    path = path or reviews_path()
    if not path.exists():
        return ReviewIndex([])
    signals, skipped = [], 0
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                signals.append(ReviewSignal.model_validate_json(line))
            except ValidationError:
                skipped += 1
    log.info("Loaded %d review signals (%d bad lines skipped)", len(signals), skipped)
    return ReviewIndex(signals)
