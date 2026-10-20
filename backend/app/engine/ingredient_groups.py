"""Sorts an ingredient (by its INCI name) into one group.

The first matching rule wins, so order matters: "behentrimonium methosulfate" is a
conditioner, not a sulfate, and "cetearyl alcohol" is a softening fatty alcohol,
not a drying one. INCI names are the same in every language.
"""

import re

from app.engine.vocab import IngredientGroup

_RULES: list[tuple[IngredientGroup, list[str]]] = [
    (
        "hold_polymer",
        [
            r"\bpvp\b",
            r"\bvp/va\b",
            r"\bvp/[a-z]+ copolymer",
            r"acrylates?\b.*(copolymer|crosspolymer)",
            r"polyquaternium-(4|11|28|46|55|69)\b",
            r"polyurethane-\d+",
            r"vinyl caprolactam",
            r"linum usitatissimum (seed )?extract|flax ?seed (extract|gel)",
        ],
    ),
    (
        "conditioning_agent",
        [
            r"trimonium",
            r"dimonium",
            r"quaternium-\d+",
            r"amidopropyl dimethylamine",
            r"\bbtms\b",
            r"althaea officinalis|ulmus fulva",  # marshmallow root, slippery elm: slip
        ],
    ),
    (
        "scalp_active",
        [
            r"salicylic acid",
            r"zinc pyrithione",
            r"piroctone olamine",
            r"ketoconazole",
            r"selenium sulfide",
            r"climbazole",
            r"tea tree|melaleuca alternifolia",
            r"rosmarinus officinalis",
            r"coal tar",
        ],
    ),
    (
        "uv_filter",
        [
            r"benzophenone-\d",
            r"ethylhexyl methoxycinnamate|octinoxate",
            r"octocrylene",
            r"butyl methoxydibenzoylmethane|avobenzone",
            r"ethylhexyl salicylate|octisalate|homosalate",
            r"polysilicone-15",
            r"benzotriazolyl",
        ],
    ),
    (
        "sulfate",
        [
            r"(lauryl|laureth|coco|myreth|trideceth|tridecyl|alkyl)[\s-]*sulfate",
            r"olefin sulfonate",
        ],
    ),
    (
        "gentle_surfactant",
        [
            r"betaine",
            r"glucoside",
            r"isethionate",
            r"sarcosinate",
            r"sulfosuccinate",
            r"ampho(di)?acetate",
            r"cocoyl glutamate|lauroyl glutamate",
            r"taurate",
        ],
    ),
    (
        "silicone_soluble",
        [
            r"peg-\d+.*methicone",
            r"dimethicone copolyol",
            r"\bbis-peg",
            r"cyclo(penta|hexa|tetra)siloxane|cyclomethicone",
        ],
    ),
    (
        "silicone_insoluble",
        [r"methicone", r"dimethiconol", r"siloxane", r"silsesquioxane"],
    ),
    (
        "protein",
        [
            r"hydrolyzed (?!jojoba)",
            r"keratin",
            r"collagen",
            r"silk amino|amino acids?\b",
            r"\barginine\b",
            r"rice ferment",
        ],
    ),
    ("butter", [r"butter\b", r"butyrospermum", r"cera alba|beeswax"]),
    (
        "heavy_oil",
        [
            r"(ricinus communis|castor|olea europaea|olive|cocos nucifera|coconut|persea gratissima|avocado|sesamum)[^,]*\boil\b",
            r"petrolatum",
            r"lanolin",
            r"paraffinum liquidum|mineral oil",
        ],
    ),
    (
        "light_oil",
        [
            r"argan|simmondsia|jojoba|vitis vinifera|grape ?seed|prunus amygdalus|almond|squalane",
            r"helianthus annuus|sunflower|camellia|moringa|rosa canina|rosehip|sclerocarya|marula",
            r"caprylic/capric triglyceride|coco-caprylate|isopropyl myristate|ethylhexyl palmitate",
            r"\boil\b",
        ],
    ),
    (
        "fatty_alcohol",
        [
            r"(cetyl|cetearyl|stearyl|behenyl|myristyl|lauryl|oleyl|arachidyl|c\d+-\d+) alcohol"
        ],
    ),
    (
        "drying_alcohol",
        [
            r"^alcohol$",
            r"alcohol denat",
            r"\bsd alcohol",
            r"isopropyl alcohol",
            r"\bethanol\b",
            r"ethyl alcohol",
        ],
    ),
    (
        "humectant",
        [
            r"\bglycerine?\b|\bglycerol\b",
            r"propanediol|propylene glycol|butylene glycol",
            r"panthenol",
            r"sorbitol",
            r"\bhoney\b|^mel$",
            r"aloe barbadensis|aloe vera",
            r"sodium (pca|hyaluronate|lactate)|hyaluronic acid",
            r"\burea\b",
        ],
    ),
    ("starch", [r"starch", r"kaolin"]),
]

_COMPILED = [(group, [re.compile(p) for p in patterns]) for group, patterns in _RULES]


def classify(inci: str) -> IngredientGroup | None:
    name = inci.lower().strip()
    for group, patterns in _COMPILED:
        if any(p.search(name) for p in patterns):
            return group
    return None
