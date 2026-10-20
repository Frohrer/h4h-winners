"""Keyword rules over review text, checked on short made-up sentences."""

import pytest

from app.engine.review_text import read_review

GOOD, BAD, MEH = 1.0, -1.0, 0.0


@pytest.mark.parametrize(
    ("text", "sentiment", "helped", "hurt"),
    [
        # Problems: absent in a positive review helps, present in a negative one hurts.
        ("Finally no frizz, even after a long day.", GOOD, ["frizz_control"], []),
        ("Tames my frizz like nothing else.", GOOD, ["frizz_control"], []),
        ("Left my hair frizzy and puffy.", BAD, [], ["frizz_control"]),
        ("Not greasy at all and smells nice.", GOOD, ["lightweight"], []),
        ("It didn't weigh my curls down.", GOOD, ["lightweight"], []),
        ("Way too heavy, it weighed my hair down.", BAD, [], ["lightweight"]),
        ("A bit greasy but I love it anyway.", GOOD, [], []),
        ("Made my hair dry and crunchy.", BAD, [], ["moisture"]),
        ("I let it air dry and the result was awful.", BAD, [], []),
        ("Works fine with dry shampoo, but it was awful.", BAD, [], []),
        ("No more tangles on wash day.", GOOD, ["detangle"], []),
        ("My hair felt limp and flat.", BAD, [], ["volume"]),
        ("Use a flat iron after.", BAD, [], []),
        ("Less breakage since I started.", GOOD, ["protein"], []),
        ("My scalp is not itchy anymore.", GOOD, ["scalp_care"], []),
        ("It made my scalp itch for days.", BAD, [], ["scalp_care"]),
        ("This gel flakes everywhere.", BAD, [], []),
        ("I was itching to try it.", GOOD, [], []),
        # Benefits: present in a positive review helps, absent in a negative one hurts.
        ("So soft and moisturized.", GOOD, ["moisture"], []),
        ("Not moisturizing at all.", BAD, [], ["moisture"]),
        ("Gorgeous definition and clumps.", GOOD, ["definition"], []),
        ("I definitely recommend it.", GOOD, [], []),
        ("No definition whatsoever.", BAD, [], ["definition"]),
        ("Great slip, combs right through.", GOOD, ["detangle"], []),
        ("Lots of volume and body.", GOOD, ["volume"], []),
        ("Hair feels stronger.", GOOD, ["protein"], []),
        ("Strong scent, though.", GOOD, [], []),
        # A benefit word in a negative review says nothing on its own.
        ("I wanted soft hair, got nothing.", BAD, [], []),
        # 3 stars: no direction.
        ("No frizz but greasy.", MEH, [], []),
    ],
)
def test_needs(text, sentiment, helped, hurt):
    signals = read_review(text, sentiment)
    assert (signals.helped, signals.hurt) == (helped, hurt)


def test_negation_stays_in_its_clause():
    signals = read_review("No complaints, but it left my hair greasy.", BAD)
    assert signals.hurt == ["lightweight"]


def test_quote_prefers_a_matching_sentence_then_a_hair_sentence():
    text = "Bought it on sale. My curls love it. Zero frizz all week!"
    assert read_review(text, GOOD).quote == "Zero frizz all week!"
    assert read_review("Bought it on sale. My curls love it.", GOOD).quote == (
        "My curls love it."
    )
    assert read_review("Bought it on sale. Arrived fast.", GOOD).quote is None
    assert read_review("Great " + "frizz " * 60, GOOD).quote is None


def test_climate():
    assert read_review("Holds up in the humidity.", GOOD).climate == "humid"
    assert read_review("Lifesaver in winter.", GOOD).climate == "very_dry_air"
    assert read_review("Nice smell.", GOOD).climate is None
