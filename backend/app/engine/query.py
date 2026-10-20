"""Reads the free-text search box: what the person wants today, and which kind of product."""

import re

from app.engine.vocab import Condition, Goal

GOAL_WORDS: list[tuple[Goal, str]] = [
    ("wash_day", r"\b(wash|co-?wash)"),
    ("define_curls", r"\b(curl|defin|coil|wash.?and.?go|ringlet|twist.?out)"),
    (
        "sleek_straight",
        r"\b(straight|sleek|flat.?iron|blow.?(out|dry)|silk.?press|smooth)",
    ),
    ("volume", r"\b(volume|big|bouncy|bounce|lift|party|full)"),
    ("refresh", r"\b(refresh|day.?(2|3|two|three)|second.?day|next.?day|revive)"),
    ("deep_clean", r"\b(clarif|deep.?clean|build.?up|swim|chlorine|pool)"),
    ("protective_style", r"\b(braid|twist|locs?\b|protective|wig|cornrow)"),
]

# Product kinds, matched against a product's category and name, and against the query.
# Order matters: "leave-in conditioner" before "conditioner", "dry shampoo" before "shampoo".
KIND_WORDS: list[tuple[str, str]] = [
    ("dry_shampoo", r"dry.?shampoo"),
    ("leave_in", r"leave.?in"),
    ("edge_control", r"\bedge"),
    ("deep_conditioner", r"deep.?condition|\bmask"),
    ("shampoo", r"shampoo|co-?wash|cleanser"),
    ("conditioner", r"conditioner"),
    ("gel", r"\bgel|jelly"),
    ("mousse", r"mousse|foam"),
    ("cream", r"cream|butter|pudding|souffl|custard|smoothie|lotion|activator"),
    ("serum", r"serum"),
    ("oil", r"\boil\b"),
    ("spray", r"spray|mist|refresher"),
]

# Climate words people type; used to warn about weather they mention, not just today's.
CLIMATE_WORDS: list[tuple[Condition, str]] = [
    ("humid", r"\b(humid|muggy|sticky|tropical|beach|rain)"),
    ("very_dry_air", r"\b(dry air|winter|desert|heater)"),
]


def goals_in(text: str) -> list[Goal]:
    t = text.lower()
    return [goal for goal, pattern in GOAL_WORDS if re.search(pattern, t)]


def kind_of(text: str) -> str:
    t = text.lower()
    return next(
        (kind for kind, pattern in KIND_WORDS if re.search(pattern, t)), "other"
    )


def product_kind(name: str, category: str) -> str:
    """The name decides when it can ("Twist Whip Butter" filed under "Leave-in")."""
    kind = kind_of(name)
    return kind if kind != "other" else kind_of(category)


def kinds_in(text: str) -> set[str]:
    """Every product kind the query names ("gel or cream" → {gel, cream})."""
    return _split_kinds(text)[0]


def without_kinds(text: str) -> str:
    """The query minus the words that named a product kind ("leave-in for frizz" → "for frizz")."""
    return _split_kinds(text)[1]


def _split_kinds(text: str) -> tuple[set[str], str]:
    found, rest = set(), text.lower()
    for kind, pattern in KIND_WORDS:
        if re.search(pattern, rest):
            found.add(kind)
            # "leave-in conditioner" names one kind, not two.
            rest = re.sub(pattern + r"\w*( conditioner)?", " ", rest)
    return found, rest


def climates_in(text: str) -> list[Condition]:
    t = text.lower()
    return [c for c, pattern in CLIMATE_WORDS if re.search(pattern, t)]
