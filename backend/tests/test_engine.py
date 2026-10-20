"""The recommendation engine, checked by values: exact weights, exact sentences, exact order."""

import pytest

from app.catalog import get_catalog
from app.engine import query
from app.engine.ingredient_groups import classify
from app.engine.needs import needs_for
from app.engine.reviews import ReviewIndex, ReviewSignal
from app.engine.scoring import analyze, explain, score
from app.environment import dew_point_band
from app.models import Environment, RecommendationRequest
from app.recommender import GraphRecommender, conditions_from

catalog = get_catalog()


def env(
    dew_point_c: float, temperature_c: float = 25, uv: float | None = None
) -> Environment:
    return Environment(
        temperature_c=temperature_c,
        relative_humidity_pct=50,
        dew_point_c=dew_point_c,
        uv_index=uv,
        dew_point_band=dew_point_band(dew_point_c),
        advice="test",
    )


def lines_of(product_id: str):
    p = catalog.get(product_id)
    return analyze(
        (
            catalog.ingredients[e.ingredient_id].name,
            catalog.ingredients[e.ingredient_id].inci,
            e.concentration_pct,
        )
        for e in p.formula
    )


@pytest.mark.parametrize(
    "inci, group",
    [
        ("Glycerin", "humectant"),
        ("Glyceryl Stearate", None),
        ("Cetearyl Alcohol", "fatty_alcohol"),
        ("Alcohol Denat.", "drying_alcohol"),
        ("Phenoxyethanol", None),
        ("Behentrimonium Methosulfate", "conditioning_agent"),
        ("Sodium Laureth Sulfate", "sulfate"),
        ("Sodium Lauroyl Sarcosinate", "gentle_surfactant"),
        ("Butyrospermum Parkii (Shea) Butter", "butter"),
        ("Cera Alba", "butter"),
        ("Ricinus Communis Seed Oil", "heavy_oil"),
        ("Melaleuca Alternifolia Leaf Oil", "scalp_active"),
        ("Simmondsia Chinensis Seed Oil", "light_oil"),
        ("Amodimethicone", "silicone_insoluble"),
        ("PEG-12 Dimethicone", "silicone_soluble"),
        ("Hydrolyzed Wheat Protein", "protein"),
        ("Lactobacillus/Rice Ferment Filtrate", "protein"),
        ("Linum Usitatissimum Seed Extract", "hold_polymer"),
        ("Polyquaternium-11", "hold_polymer"),
        ("Polyquaternium-10", "conditioning_agent"),
        ("Mel", "humectant"),
        ("Aqua", None),
    ],
)
def test_ingredient_groups(inci, group):
    assert classify(inci) == group


def test_every_seed_ingredient_that_does_something_has_a_group():
    ungrouped = {
        i.inci for i in catalog.ingredients.values() if classify(i.inci) is None
    }
    # Carriers, thickeners, preservatives, pH and scent: no effect on hair needs.
    assert ungrouped == {
        "Aqua",
        "Xanthan Gum",
        "Pyrus Malus Fruit Vinegar",
        "Phenoxyethanol",
        "Citric Acid",
        "Parfum",
    }


def test_analyze_uses_concentrations_when_every_line_has_one():
    lines = analyze([("Water", "Aqua", 80), ("Glycerin", "Glycerin", 20)])
    assert [(line.group, line.weight) for line in lines] == [
        (None, 0.8),
        ("humectant", 0.2),
    ]


def test_analyze_falls_back_to_label_order():
    lines = analyze(
        [
            ("Water", "Aqua", None),
            ("Glycerin", "Glycerin", 5),
            ("Shea", "Shea Butter", None),
        ]
    )
    # Weights 1, 0.75, 0.6 by position, normalized.
    assert [round(line.weight, 4) for line in lines] == [0.4255, 0.3191, 0.2553]


def test_needs_add_up_and_remember_why():
    n = needs_for(["4C"], porosity="high", thickness="coarse")
    assert n.weights["seal"] == 6  # 4C 3 + high porosity 2 + coarse 1
    assert n.weights["moisture"] == 5  # 4C 3 + high porosity 1 + coarse 1
    assert n.because["seal"] == [
        "for your 4C hair",
        "for your high-porosity hair",
        "for your coarse strands",
    ]


def test_several_hair_types_share_one_vote():
    n = needs_for(["3C", "4A"])
    assert n.weights["moisture"] == 2.5  # (3C 2 + 4A 3) / 2
    assert n.why("moisture") is None  # the page already says the hair type


def test_weather_is_named_first_in_reasons():
    n = needs_for(["3B"], conditions=["humid"])
    assert n.why("frizz_control") == "for today's humid air"
    assert n.why("definition") is None


@pytest.mark.parametrize(
    "environment, conditions",
    [
        (None, []),
        (env(10), []),
        (env(18), ["humid"]),
        (env(22), ["very_humid"]),
        (env(-5), ["very_dry_air"]),
        (env(-5, temperature_c=0), ["very_dry_air", "cold"]),
        (env(10, uv=7), ["strong_sun"]),
    ],
)
def test_conditions_from_environment(environment, conditions):
    assert conditions_from(environment) == conditions


def test_glycerin_is_a_plus_on_a_mild_day_and_a_warning_on_a_dry_one():
    lines = analyze([("Water", "Aqua", 80), ("Glycerin", "Glycerin", 20)])

    mild = needs_for(["4C"])
    assert explain(score(lines, mild)[1], mild) == (
        ["Glycerin adds moisture"],
        [],
    )

    dry = needs_for(["4C"], conditions=["very_dry_air"])
    assert explain(score(lines, dry, ["very_dry_air"])[1], dry) == (
        [],
        ["Glycerin can dry hair out in today's dry air"],
    )


def test_dry_day_reasons_for_a_real_seed_product():
    n = needs_for(["4C"], conditions=["very_dry_air"])
    _, contributions = score(
        lines_of("coilwell-whipped-shea-curl-cream"), n, ["very_dry_air"]
    )
    reasons, warnings = explain(contributions, n)
    assert warnings == [
        "Aloe vera juice and glycerin can dry hair out in today's dry air"
    ]
    # Coconut oil seals but adds no moisture of its own (rules table C), so it's not in line 2.
    assert reasons == [
        "Shea butter and coconut oil lock moisture in for today's dry air",
        "Shea butter and cetearyl alcohol add moisture for today's dry air",
        "BTMS and cetearyl alcohol add slip for detangling",
    ]


@pytest.mark.parametrize(
    "text, kinds",
    [
        ("leave-in conditioner", {"leave_in"}),
        ("dry shampoo", {"dry_shampoo"}),
        ("deep conditioner for breakage", {"deep_conditioner"}),
        ("gel or cream", {"gel", "cream"}),
        ("edges", {"edge_control"}),
        ("something for my curls", set()),
    ],
)
def test_kinds_in_query(text, kinds):
    assert query.kinds_in(text) == kinds


def test_goals_and_climate_in_query():
    assert query.goals_in("party tonight, want big defined curls") == [
        "define_curls",
        "volume",
    ]
    assert query.climates_in("beach trip next week") == ["humid"]


def test_reviews_trust_many_more_than_few_and_near_types_less():
    def r(hair_type):
        return ReviewSignal(product_id="x", hair_type=hair_type, sentiment=1)

    assert ReviewIndex([r("3C")]).evidence("x", ["3C"]).score == pytest.approx(1 / 6)
    assert ReviewIndex([r("3C")] * 20).evidence("x", ["3C"]).score == pytest.approx(
        20 / 25
    )
    near = ReviewIndex([r("4A")]).evidence("x", ["3C"])
    assert near.score == pytest.approx(0.65 / 5.65)
    assert near.summary is None


def test_reviews_add_their_trusted_share_and_many_can_change_the_order():
    request = RecommendationRequest(hair_types=["4C"], query="deep conditioner")

    def ranked(reviews):
        results = GraphRecommender(catalog, ReviewIndex(reviews)).recommend(
            request, None
        )
        return {r.product.id: r.score for r in results}, [r.product.id for r in results]

    scores, order = ranked([])
    assert order == ["moss-honey-hydration-mask", "coilwell-protein-rescue-mask"]
    underdog = order[1]

    def happy(n):
        signal = ReviewSignal(
            product_id=underdog, hair_type="4C", sentiment=1, helped=["moisture"]
        )
        return [signal] * n

    # REVIEW_WEIGHT 0.5 × trust n / (n + 5).
    one, _ = ranked(happy(1))
    assert one[underdog] - scores[underdog] == pytest.approx(0.5 / 6, abs=1e-3)
    thirty, order_after = ranked(happy(30))
    assert thirty[underdog] - scores[underdog] == pytest.approx(0.5 * 30 / 35, abs=1e-3)
    assert order_after == [underdog, order[0]]

    top = GraphRecommender(catalog, ReviewIndex(happy(30))).recommend(request, None)[0]
    assert "30 of 30 reviewers with 4C hair liked it: it adds moisture" in top.reasons


def test_query_kind_filters_results():
    request = RecommendationRequest(hair_types=["3B"], query="leave-in")
    results = GraphRecommender(catalog, ReviewIndex([])).recommend(request, None)
    assert {r.product.category for r in results} == {"Leave-in conditioner"}
