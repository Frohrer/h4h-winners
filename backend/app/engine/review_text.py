"""Reads a review's text: which needs a product helped or hurt, one quote, the climate.

Simple keyword rules, tuned for precision over recall: a rule that is unsure says
nothing. The star rating sets the direction, so a positive review only ever yields
`helped` and a negative one only `hurt`; a 3-star review yields neither.

Two kinds of words:
- problems ("frizz", "greasy"): absent ("no frizz", "not greasy", "frizz-free") in a
  positive review → helped; present in a negative review → hurt. Present in a positive
  review counts as helped only where reviewers mostly mean the product fixed it
  ("tames my frizz"), not where it's a complaint they forgave ("a bit greasy but…").
- benefits ("soft", "defined"): present in a positive review → helped; absent
  ("not moisturizing") in a negative review → hurt.
"""

import re
from dataclasses import dataclass, field

from app.engine.vocab import Condition, Need


@dataclass(frozen=True)
class Rule:
    need: Need
    pattern: str
    problem: bool  # names a problem (frizz) rather than a benefit (soft)
    present_in_positive_helps: bool = False  # problems only: "tames my frizz"
    requires: str | None = None  # the sentence must also match this


# fmt: off
RULES = [
    Rule("frizz_control", r"\bfrizz", problem=True, present_in_positive_helps=True),
    Rule("lightweight", r"\bweigh(s|ed|ing)?( \w+){0,2} down|\bgreas(y|iness)|\bheavy\b|\bbuild ?-?up|\boily\b", problem=True),
    # "air dry", "dry shampoo" and "dry scalp" aren't the product drying hair out.
    Rule("moisture", r"(?<!air )(?<!blow )(?<!towel )(?<!to )\bdry\b(?! (shampoo|time|climate|weather|scalp|skin))|\bdried (it |my hair )?out\b|\bcrunchy\b|\bstraw\b|\bbrittle\b", problem=True),
    Rule("moisture", r"\bsoft|\bmoistur|\bhydrat", problem=False),
    # "definitely" is not definition.
    Rule("definition", r"\bdefin(e|es|ed|ing|ition)\b|\bclump|\bcurl pattern", problem=False),
    Rule("detangle", r"(?<!de)tangl|\bknots?\b", problem=True, present_in_positive_helps=True),
    Rule("detangle", r"\bdetangl|\bslip\b|\bcombs? (right )?through", problem=False),
    Rule("volume", r"\bvolum|\bbody\b(?! (wash|lotion|butter|oil|cream|spray|soap))", problem=False),
    Rule("volume", r"\bflat\b(?! ?-?(iron|twist))|\blimp\b|\blifeless\b", problem=True),
    Rule("protein", r"\bbreak(age|ing|s)?\b(?! (the|a|my) cast| out)|\bsnap(s|ping)?\b", problem=True),
    Rule("protein", r"\bstrong(er)?\b(?! (scent|smell|fragrance|hold|odou?r|perfume))|\bstrength", problem=False),
    # Gel flakes and "itching to try" are not scalp problems: the sentence must be about the scalp.
    Rule("scalp_care", r"\bitch|\bflak|\bdandruff|\birritat", problem=True, present_in_positive_helps=True, requires=r"\bscalp|\bdandruff"),
]
# fmt: on

# Words that mean the thing just after them is absent ("no frizz", "didn't weigh it down").
NEGATION = re.compile(
    r"\b(no|not|never|without|zero|none|nor|hardly|barely|less|minimal|reduced?|"
    r"cannot|(do|does|did|is|was|are|were|wo|ca|could|would|has|have)n['’]?t)\b"
)
NEGATION_WINDOW = 4  # words before the match, within the same clause
FREE_AFTER = re.compile(r"^[- ]?free\b")
CLAUSE_BREAK = re.compile(r"[,;:]|\bbut\b|\bhowever\b|\bthough\b")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
HAIR_WORD = re.compile(r"\b(hair|curls?|coils?|waves?|strands?|scalp)\b")
QUOTE_MAX = 200

CLIMATE_WORDS: list[tuple[Condition, str]] = [
    ("humid", r"\bhumid(ity)?\b"),
    ("very_dry_air", r"\bdry (climate|air)\b|\bwinter\b"),
]


@dataclass
class TextSignals:
    helped: list[Need] = field(default_factory=list)
    hurt: list[Need] = field(default_factory=list)
    quote: str | None = None
    climate: Condition | None = None


def _negated(sentence: str, start: int, end: int) -> bool:
    before = CLAUSE_BREAK.split(sentence[:start])[-1]
    words = before.split()[-NEGATION_WINDOW:]
    if NEGATION.search(" ".join(words)):
        return True
    return bool(FREE_AFTER.match(sentence[end:]))


def _effect(rule: Rule, negated: bool, sentiment: float) -> str | None:
    """'helped', 'hurt' or None for one keyword hit."""
    if sentiment > 0:
        if rule.problem:
            return "helped" if negated or rule.present_in_positive_helps else None
        return None if negated else "helped"
    if sentiment < 0:
        if rule.problem:
            return None if negated else "hurt"
        return "hurt" if negated else None
    return None


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE.split(text) if s.strip()]


def read_review(text: str, sentiment: float) -> TextSignals:
    out = TextSignals()
    first_hit = first_hair = None
    for sentence in sentences(text):
        s = sentence.lower()
        hit = False
        for rule in RULES:
            if rule.requires and not re.search(rule.requires, s):
                continue
            for m in re.finditer(rule.pattern, s):
                hit = True
                effect = _effect(rule, _negated(s, m.start(), m.end()), sentiment)
                target = out.helped if effect == "helped" else out.hurt
                if effect and rule.need not in target:
                    target.append(rule.need)
        if len(sentence) <= QUOTE_MAX:
            if hit and first_hit is None:
                first_hit = sentence
            if first_hair is None and HAIR_WORD.search(s):
                first_hair = sentence
    out.quote = first_hit or first_hair
    lowered = text.lower()
    out.climate = next(
        (c for c, pattern in CLIMATE_WORDS if re.search(pattern, lowered)), None
    )
    return out
