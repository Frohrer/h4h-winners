"""Shared ids for needs, ingredient groups and weather conditions.

Reviews (`helped` / `hurt` in reviews.jsonl) use the NEEDS ids, so the review
pipeline and the rules line up.
"""

from typing import Literal

HAIR_TYPES = [f"{n}{c}" for n in "1234" for c in "ABC"]

Need = Literal[
    "moisture",
    "seal",
    "protein",
    "lightweight",
    "definition",
    "frizz_control",
    "volume",
    "smoothness",
    "gentle_cleanse",
    "clarify",
    "detangle",
    "heat_protection",
    "uv_protection",
    "scalp_care",
]

# How a reason reads when an ingredient helps a need: "Glycerin adds moisture".
HELPS: dict[str, str] = {
    "moisture": "adds moisture",
    "seal": "locks moisture in",
    "protein": "strengthens strands",
    "lightweight": "stays light",
    "definition": "defines and holds",
    "frizz_control": "fights frizz",
    "volume": "adds volume",
    "smoothness": "smooths",
    "gentle_cleanse": "cleans gently",
    "clarify": "removes build-up",
    "detangle": "adds slip for detangling",
    "heat_protection": "protects from heat",
    "uv_protection": "protects from sun",
    "scalp_care": "soothes the scalp",
}

# How a warning reads when an ingredient works against a need: "Shea butter can weigh hair down".
HURTS: dict[str, str] = {
    "moisture": "can dry hair out",
    "seal": "won't lock moisture in",
    "protein": "can weaken strands",
    "lightweight": "can weigh hair down",
    "definition": "can loosen curls",
    "frizz_control": "can cause frizz",
    "volume": "can flatten hair",
    "smoothness": "can rough up hair",
    "gentle_cleanse": "is a harsh cleanser",
    "clarify": "can build up",
    "detangle": "can make tangles worse",
    "heat_protection": "won't protect from heat",
    "uv_protection": "won't protect from sun",
    "scalp_care": "can irritate the scalp",
}

IngredientGroup = Literal[
    "humectant",
    "protein",
    "butter",
    "heavy_oil",
    "light_oil",
    "silicone_insoluble",
    "silicone_soluble",
    "fatty_alcohol",
    "drying_alcohol",
    "sulfate",
    "gentle_surfactant",
    "conditioning_agent",
    "hold_polymer",
    "uv_filter",
    "scalp_active",
    "starch",
]

Condition = Literal["very_dry_air", "humid", "very_humid", "strong_sun", "cold"]

CONDITION_LABELS: dict[str, str] = {
    "very_dry_air": "dry air",
    "humid": "humid air",
    "very_humid": "very humid air",
    "strong_sun": "strong sun",
    "cold": "cold",
}

Goal = Literal[
    "wash_day",
    "define_curls",
    "sleek_straight",
    "volume",
    "refresh",
    "deep_clean",
    "protective_style",
]
