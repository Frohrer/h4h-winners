"""Adds up what a person's hair needs right now, and remembers why.

Each need keeps the phrases that asked for it ("for your 4C hair", "for today's humid
air"), so reasons can say who the ingredient is for.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.engine.rules import (
    COLOR_TREATED_NEEDS,
    CONDITION_NEEDS,
    DENSITY_NEEDS,
    GOAL_NEEDS,
    HAIR_TYPE_NEEDS,
    POROSITY_NEEDS,
    SCALP_NEEDS,
    THICKNESS_NEEDS,
    NeedVector,
)
from app.engine.vocab import CONDITION_LABELS, Condition, Goal


@dataclass
class Needs:
    weights: dict[str, float] = field(default_factory=dict)
    because: dict[str, list[str]] = field(default_factory=dict)
    # Needs raised by today's weather; reasons mention the weather first for these.
    weather_because: dict[str, str] = field(default_factory=dict)
    # Phrases the page already says ("For 4C hair"), so reasons don't repeat them.
    quiet: set[str] = field(default_factory=set)

    def add(self, vector: NeedVector, why: str, factor: float = 1.0) -> None:
        for need, value in vector.items():
            self.weights[need] = self.weights.get(need, 0) + value * factor
            if value > 0:
                self.because.setdefault(need, []).append(why)

    def why(self, need: str) -> str | None:
        """The phrase a reason should end with: the weather if it asked, else the
        first asker the page doesn't already name, else nothing."""
        if need in self.weather_because:
            return self.weather_because[need]
        return next(
            (w for w in self.because.get(need, []) if w not in self.quiet), None
        )


def needs_for(
    hair_types: list[str],
    *,
    porosity: str | None = None,
    thickness: str | None = None,
    density: str | None = None,
    scalp: str | None = None,
    color_treated: bool = False,
    goals: Iterable[Goal] = (),
    conditions: Iterable[Condition] = (),
) -> Needs:
    n = Needs()
    known = [t for t in hair_types if t in HAIR_TYPE_NEEDS]
    # Several types (people often have more than one pattern) share one vote.
    hair_phrase = f"for your {'/'.join(known)} hair"
    n.quiet.add(hair_phrase)
    for t in known:
        n.add(HAIR_TYPE_NEEDS[t], hair_phrase, 1 / len(known))
    if porosity:
        n.add(POROSITY_NEEDS[porosity], f"for your {porosity}-porosity hair")
    if thickness:
        n.add(THICKNESS_NEEDS[thickness], f"for your {thickness} strands")
    if density:
        n.add(DENSITY_NEEDS[density], f"for your {density}-density hair")
    if scalp:
        n.add(SCALP_NEEDS[scalp], f"for your {scalp} scalp")
    if color_treated:
        n.add(COLOR_TREATED_NEEDS, "for your colored hair")
    n.quiet.add("for your search")
    for g in goals:
        n.add(GOAL_NEEDS[g], "for your search")
    for c in conditions:
        phrase = f"for today's {CONDITION_LABELS[c]}"
        n.add(CONDITION_NEEDS[c], phrase)
        for need in CONDITION_NEEDS[c]:
            n.weather_because.setdefault(need, phrase)
    return n
