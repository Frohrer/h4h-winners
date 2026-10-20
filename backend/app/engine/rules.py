"""The recipe book. Every number says how strongly one thing pushes a need, from -3
(works against it) to +3 (strongly wants it / strongly delivers it).

These tables are the knobs to tune; the engine itself has no hair knowledge.
"""

from app.engine.vocab import Condition, Goal, IngredientGroup, Need

NeedVector = dict[Need, float]

# --- A. Your hair → what it needs ----------------------------------------------

HAIR_TYPE_NEEDS: dict[str, NeedVector] = {
    "1A": {"lightweight": 3, "volume": 2},
    "1B": {"lightweight": 2, "volume": 1, "smoothness": 1},
    "1C": {"lightweight": 1, "frizz_control": 1, "smoothness": 1},
    "2A": {"lightweight": 2, "definition": 1, "frizz_control": 1},
    "2B": {"lightweight": 1, "definition": 2, "frizz_control": 1},
    "2C": {"definition": 2, "frizz_control": 2, "moisture": 1},
    "3A": {"definition": 2, "frizz_control": 2, "moisture": 1},
    "3B": {"definition": 2, "frizz_control": 2, "moisture": 2, "gentle_cleanse": 1},
    "3C": {
        "definition": 2,
        "frizz_control": 2,
        "moisture": 2,
        "seal": 1,
        "detangle": 1,
        "gentle_cleanse": 1,
    },
    "4A": {
        "moisture": 3,
        "seal": 2,
        "definition": 2,
        "detangle": 1,
        "gentle_cleanse": 1,
    },
    "4B": {
        "moisture": 3,
        "seal": 2,
        "detangle": 2,
        "definition": 1,
        "gentle_cleanse": 2,
    },
    "4C": {"moisture": 3, "seal": 3, "detangle": 2, "gentle_cleanse": 2},
}

POROSITY_NEEDS: dict[str, NeedVector] = {
    "low": {"lightweight": 2, "moisture": 1, "clarify": 1},
    "medium": {},
    "high": {"protein": 2, "seal": 2, "moisture": 1, "frizz_control": 1},
}

THICKNESS_NEEDS: dict[str, NeedVector] = {
    "fine": {"lightweight": 3, "protein": 1, "volume": 1},
    "medium": {},
    "coarse": {"moisture": 1, "seal": 1, "lightweight": -1},
}

DENSITY_NEEDS: dict[str, NeedVector] = {
    "low": {"lightweight": 1, "volume": 1},
    "medium": {},
    "high": {"moisture": 1, "detangle": 1},
}

SCALP_NEEDS: dict[str, NeedVector] = {
    "normal": {},
    "oily": {"clarify": 1, "lightweight": 1},
    "dry": {"scalp_care": 2, "gentle_cleanse": 1},
    "flaky": {"scalp_care": 3},
}

COLOR_TREATED_NEEDS: NeedVector = {"gentle_cleanse": 2, "uv_protection": 1}

# --- B. Today → what it needs ----------------------------------------------------

GOAL_NEEDS: dict[Goal, NeedVector] = {
    "wash_day": {"gentle_cleanse": 1, "moisture": 1, "detangle": 1},
    "define_curls": {"definition": 3, "frizz_control": 1},
    "sleek_straight": {"smoothness": 3, "heat_protection": 3, "frizz_control": 2},
    "volume": {"volume": 3, "lightweight": 2},
    "refresh": {"moisture": 1, "definition": 1},
    "deep_clean": {"clarify": 3},
    "protective_style": {"seal": 2, "moisture": 1, "scalp_care": 1},
}

CONDITION_NEEDS: dict[Condition, NeedVector] = {
    "very_dry_air": {"seal": 2, "moisture": 1},
    "humid": {"frizz_control": 2},
    "very_humid": {"frizz_control": 3, "definition": 2},
    "strong_sun": {"uv_protection": 2, "moisture": 1},
    "cold": {"seal": 1, "moisture": 1},
}

# --- C. Ingredient group → which needs it delivers or works against -------------

GROUP_EFFECTS: dict[IngredientGroup, NeedVector] = {
    "humectant": {"moisture": 2, "lightweight": 1},
    "protein": {"protein": 3, "definition": 1, "moisture": -1},
    "butter": {
        "seal": 3,
        "moisture": 1,
        "frizz_control": 1,
        "smoothness": 1,
        "lightweight": -3,
        "volume": -2,
    },
    "heavy_oil": {
        "seal": 2,
        "smoothness": 1,
        "frizz_control": 1,
        "lightweight": -2,
        "volume": -1,
    },
    "light_oil": {"seal": 1, "smoothness": 1, "frizz_control": 1},
    "silicone_insoluble": {
        "smoothness": 3,
        "frizz_control": 2,
        "heat_protection": 2,
        "detangle": 2,
        "lightweight": -1,
        "clarify": -2,
    },
    "silicone_soluble": {"smoothness": 1, "frizz_control": 1, "detangle": 1},
    "fatty_alcohol": {"moisture": 1, "detangle": 1, "smoothness": 1},
    "drying_alcohol": {"moisture": -2, "lightweight": 1, "volume": 1},
    "sulfate": {"clarify": 3, "gentle_cleanse": -3, "moisture": -2, "volume": 1},
    "gentle_surfactant": {"gentle_cleanse": 2, "clarify": 1},
    "conditioning_agent": {
        "detangle": 3,
        "smoothness": 1,
        "moisture": 1,
        "frizz_control": 1,
    },
    "hold_polymer": {"definition": 3, "frizz_control": 2, "volume": 1},
    "uv_filter": {"uv_protection": 3},
    "scalp_active": {"scalp_care": 3},
    "starch": {"volume": 2, "lightweight": 1, "clarify": 1},
}

# Weather changes what some ingredients do. Glycerin pulls water from the air: on a
# humid day that swells the hair (frizz), on a very dry day it pulls water out.
CONDITION_GROUP_EFFECTS: dict[Condition, dict[IngredientGroup, NeedVector]] = {
    "humid": {"humectant": {"frizz_control": -2}},
    "very_humid": {"humectant": {"frizz_control": -3, "definition": -1}},
    "very_dry_air": {"humectant": {"moisture": -3}},
}
