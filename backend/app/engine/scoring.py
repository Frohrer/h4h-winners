"""Scores one product against a set of needs and explains the score in plain words.

A product's score is the sum, over its ingredients, of
  share of the bottle × what the ingredient's group does to a need × how much that need matters,
divided by the total need weight so scores are comparable between people.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.engine.ingredient_groups import classify
from app.engine.needs import Needs
from app.engine.rules import CONDITION_GROUP_EFFECTS, GROUP_EFFECTS
from app.engine.vocab import CONDITION_LABELS, HELPS, HURTS, Condition, IngredientGroup

# Scores are normalized, so these are shares of the whole score.
REASON_MIN = 0.01
WARNING_MIN = 0.015


@dataclass(frozen=True)
class Line:
    name: str
    group: IngredientGroup | None
    weight: float  # share of the bottle, all lines sum to 1


def position_weight(i: int) -> float:
    """Labels list the biggest amounts first: spot 1 counts 1, spot 4 half, spot 10 a quarter."""
    return 1 / (1 + i / 3)


def analyze(entries: Iterable[tuple[str, str, float | None]]) -> list[Line]:
    """entries: (display name, INCI name, concentration % or None) in label order."""
    entries = list(entries)
    if entries and all(pct is not None for _, _, pct in entries):
        raw = [pct for _, _, pct in entries]
    else:
        raw = [position_weight(i) for i in range(len(entries))]
    total = sum(raw) or 1
    return [
        Line(name=name, group=classify(inci), weight=w / total)
        for (name, inci, _), w in zip(entries, raw, strict=True)
    ]


@dataclass(frozen=True)
class Contribution:
    ingredient: str
    group: IngredientGroup
    need: str
    effect: float  # what the group does to the need, before weighting
    # Set when the effect only exists because of the weather.
    condition: Condition | None
    points: float


def score(
    lines: list[Line], needs: Needs, conditions: Iterable[Condition] = ()
) -> tuple[float, list[Contribution]]:
    norm = sum(abs(w) for w in needs.weights.values()) or 1
    out: list[Contribution] = []
    for line in lines:
        if line.group is None:
            continue
        effects = [(GROUP_EFFECTS[line.group], None)]
        effects += [
            (CONDITION_GROUP_EFFECTS[c][line.group], c)
            for c in conditions
            if line.group in CONDITION_GROUP_EFFECTS.get(c, {})
        ]
        for vector, condition in effects:
            for need, effect in vector.items():
                weight = needs.weights.get(need)
                if weight:
                    points = line.weight * effect * weight / norm
                    out.append(
                        Contribution(
                            line.name, line.group, need, effect, condition, points
                        )
                    )
    return sum(c.points for c in out), out


def _join(names: list[str]) -> str:
    """Joins up to two names; later ones lowercased unless they're acronyms (BTMS)."""
    rest = [n if n[:2].isupper() else n[:1].lower() + n[1:] for n in names[1:2]]
    return " and ".join([names[0], *rest])


def _verb(phrase: str, plural: bool) -> str:
    """Makes the verb plural when two ingredients share a sentence (adds → add)."""
    if not plural:
        return phrase
    if phrase.startswith("is a "):
        return f"are {phrase[5:]}s"  # "is a harsh cleanser" → "are harsh cleansers"
    first, _, rest = phrase.partition(" ")
    if first.endswith("s") and not first.endswith("ss"):
        first = first[:-1]
    return f"{first} {rest}".strip()


def explain(
    contributions: list[Contribution], needs: Needs
) -> tuple[list[str], list[str]]:
    """Up to 3 reasons ("Glycerin adds moisture for your 4C hair") and 2 warnings.

    Each ingredient is judged by its net effect on a need, weather included, so glycerin
    on a dry day shows up as a warning and never also as a reason.
    """
    net: dict[tuple[str, str], float] = {}
    # The weather condition that pushed an ingredient's effect down the most.
    blame: dict[tuple[str, str], tuple[float, Condition]] = {}
    for c in contributions:
        key = (c.ingredient, c.need)
        net[key] = net.get(key, 0) + c.points
        if c.condition and c.points < blame.get(key, (0, None))[0]:
            blame[key] = (c.points, c.condition)

    helps: dict[str, list[tuple[str, float]]] = {}
    hurts: dict[tuple[str, Condition | None], list[tuple[str, float]]] = {}
    for (ingredient, need), points in net.items():
        if needs.weights.get(need, 0) <= 0:
            continue
        if points > 0:
            helps.setdefault(need, []).append((ingredient, points))
        elif points < 0:
            condition = blame.get((ingredient, need), (0, None))[1]
            hurts.setdefault((need, condition), []).append((ingredient, points))

    reasons = []
    for need, items in sorted(helps.items(), key=lambda kv: -sum(p for _, p in kv[1])):
        if sum(p for _, p in items) < REASON_MIN or len(reasons) == 3:
            continue
        names = [n for n, _ in sorted(items, key=lambda x: -x[1])][:2]
        why = needs.why(need)
        reasons.append(
            f"{_join(names)} {_verb(HELPS[need], len(names) > 1)}"
            + (f" {why}" if why else "")
        )

    warnings = []
    for (need, condition), items in sorted(
        hurts.items(), key=lambda kv: sum(p for _, p in kv[1])
    ):
        if sum(p for _, p in items) > -WARNING_MIN or len(warnings) == 2:
            continue
        names = [n for n, _ in sorted(items, key=lambda x: x[1])][:2]
        text = f"{_join(names)} {_verb(HURTS[need], len(names) > 1)}"
        warnings.append(
            text + (f" in today's {CONDITION_LABELS[condition]}" if condition else "")
        )
    return reasons, warnings
