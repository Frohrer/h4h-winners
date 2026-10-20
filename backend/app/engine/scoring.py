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


def analyze(entries: Iterable[tuple[str, str]]) -> list[Line]:
    """entries: (display name, INCI name) in label order."""
    entries = list(entries)
    raw = [position_weight(i) for i in range(len(entries))]
    total = sum(raw) or 1
    return [
        Line(name=name, group=classify(inci), weight=w / total)
        for (name, inci), w in zip(entries, raw, strict=True)
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


def _effects(
    group: IngredientGroup, conditions: Iterable[Condition]
) -> list[tuple[dict[str, float], Condition | None]]:
    """The group's own effects, then whatever today's weather adds or takes away."""
    effects = [(GROUP_EFFECTS[group], None)]
    effects += [
        (CONDITION_GROUP_EFFECTS[c][group], c)
        for c in conditions
        if group in CONDITION_GROUP_EFFECTS.get(c, {})
    ]
    return effects


def score(
    lines: list[Line], needs: Needs, conditions: Iterable[Condition] = ()
) -> tuple[float, list[Contribution]]:
    norm = sum(abs(w) for w in needs.weights.values()) or 1
    out: list[Contribution] = []
    for line in lines:
        if line.group is None:
            continue
        for vector, condition in _effects(line.group, conditions):
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


@dataclass(frozen=True)
class Delivery:
    """What a product delivers per need, worked out once per product.

    Scoring with it gives the same number as score(), without walking the
    ingredients again for every request.
    """

    base: dict[str, float]
    by_condition: dict[str, dict[str, float]]


def delivery(lines: list[Line]) -> Delivery:
    base: dict[str, float] = {}
    by_condition: dict[str, dict[str, float]] = {}
    for line in lines:
        if line.group is None:
            continue
        for need, effect in GROUP_EFFECTS[line.group].items():
            base[need] = base.get(need, 0) + line.weight * effect
        for condition, groups in CONDITION_GROUP_EFFECTS.items():
            for need, effect in groups.get(line.group, {}).items():
                extra = by_condition.setdefault(condition, {})
                extra[need] = extra.get(need, 0) + line.weight * effect
    return Delivery(base, by_condition)


def quick_score(
    d: Delivery, needs: Needs, conditions: Iterable[Condition] = ()
) -> float:
    norm = sum(abs(w) for w in needs.weights.values()) or 1
    total = sum(w * d.base.get(need, 0) for need, w in needs.weights.items())
    for c in conditions:
        extra = d.by_condition.get(c, {})
        total += sum(w * extra.get(need, 0) for need, w in needs.weights.items())
    return total / norm


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
    parts = []
    for part in phrase.split(" and "):  # "defines and holds" → "define and hold"
        first, _, rest = part.partition(" ")
        if first.endswith("s") and not first.endswith("ss"):
            first = first[:-1]
        parts.append(f"{first} {rest}".strip())
    return " and ".join(parts)


def _net(
    contributions: list[Contribution],
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], Condition]]:
    """Net points per (ingredient, need), and the weather condition that pushed each
    one down the most."""
    net: dict[tuple[str, str], float] = {}
    blame: dict[tuple[str, str], tuple[float, Condition]] = {}
    for c in contributions:
        key = (c.ingredient, c.need)
        net[key] = net.get(key, 0) + c.points
        if c.condition and c.points < blame.get(key, (0, None))[0]:
            blame[key] = (c.points, c.condition)
    return net, {key: condition for key, (_, condition) in blame.items()}


def _split(
    contributions: list[Contribution], needs: Needs
) -> tuple[
    dict[str, list[tuple[str, float]]],
    dict[tuple[str, Condition | None], list[tuple[str, float]]],
]:
    """Groups ingredients that help a wanted need, and those that hurt one (by need and
    the weather to blame)."""
    net, blame = _net(contributions)
    helps: dict[str, list[tuple[str, float]]] = {}
    hurts: dict[tuple[str, Condition | None], list[tuple[str, float]]] = {}
    for (ingredient, need), points in net.items():
        if needs.weights.get(need, 0) <= 0:
            continue
        if points > 0:
            helps.setdefault(need, []).append((ingredient, points))
        elif points < 0:
            condition = blame.get((ingredient, need))
            hurts.setdefault((need, condition), []).append((ingredient, points))
    return helps, hurts


def _reasons(helps: dict[str, list[tuple[str, float]]], needs: Needs) -> list[str]:
    # Same ingredients helping two needs read as one line: "add moisture and stay light".
    lines: dict[tuple[tuple[str, ...], str | None], list[str]] = {}
    for need, items in sorted(helps.items(), key=lambda kv: -sum(p for _, p in kv[1])):
        if sum(p for _, p in items) < REASON_MIN:
            continue
        names = tuple(n for n, _ in sorted(items, key=lambda x: -x[1])[:2])
        key = (names, needs.why(need))
        if key in lines or len(lines) < 3:
            lines.setdefault(key, []).append(_verb(HELPS[need], len(names) > 1))
    return [
        f"{_join(list(names))} {' and '.join(phrases)}" + (f" {why}" if why else "")
        for (names, why), phrases in lines.items()
    ]


def _warnings(
    hurts: dict[tuple[str, Condition | None], list[tuple[str, float]]],
) -> list[str]:
    warnings, warned = [], set()
    for (need, condition), items in sorted(
        hurts.items(), key=lambda kv: sum(p for _, p in kv[1])
    ):
        if sum(p for _, p in items) > -WARNING_MIN or len(warnings) == 2:
            continue
        names = [n for n, _ in sorted(items, key=lambda x: x[1])][:2]
        # One warning per ingredient: the worst thing it does.
        if tuple(names) in warned:
            continue
        warned.add(tuple(names))
        text = f"{_join(names)} {_verb(HURTS[need], len(names) > 1)}"
        warnings.append(
            text + (f" in today's {CONDITION_LABELS[condition]}" if condition else "")
        )
    return warnings


def explain(
    contributions: list[Contribution], needs: Needs
) -> tuple[list[str], list[str]]:
    """Up to 3 reasons ("Glycerin adds moisture for your 4C hair") and 2 warnings.

    Each ingredient is judged by its net effect on a need, weather included, so glycerin
    on a dry day shows up as a warning and never also as a reason.
    """
    helps, hurts = _split(contributions, needs)
    return _reasons(helps, needs), _warnings(hurts)
