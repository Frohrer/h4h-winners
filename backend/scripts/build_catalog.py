"""Builds /data/generated/catalog.json from the scraped product files.

Run inside the backend container:
    uv run --frozen python scripts/build_catalog.py

Sources, best first (the first one wins when a product appears twice):
retail (hand-checked demo products), brands (brand websites), amazon_2023,
open_beauty_facts. influenster_2017 is skipped for licensing, bazaarvoice has
no ingredients.
"""

import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog import SEED_PATH, CatalogFile
from app.engine.inci import display_name, ingredient_key, parse_inci
from app.engine.ingredient_groups import classify
from app.engine.query import product_kind
from app.engine.vocab import HAIR_TYPES
from app.ids import product_key

DATA = Path("/data")
OUT = DATA / "generated" / "catalog.json"
SOURCES = ["retail", "brands", "amazon_2023", "open_beauty_facts"]
MIN_INGREDIENTS = 5
MAX_DESCRIPTION = 600

# Not formulas you'd recommend by hair type: color, chemical treatments, multi-product sets.
EXCLUDE = re.compile(
    r"\b(hair colou?r|colou?r (correct|refresh)\w*|dyes?|colou?rants?|coloration|hennas?"
    r"|chalk|relaxers?|perm|bleach|straighteners?|depilat\w*"
    r"|sets?|kits?|duo|trio|bundle|gift)\b",
    re.IGNORECASE,
)

# The seed catalog's tints.
PALETTE = [
    "#6E9E7A", "#6FA89A", "#7FA36B", "#7FA7C9", "#8FBF9F", "#9BB7D4", "#A8C3D6",
    "#A9D3D0", "#B8C76A", "#B9834F", "#C7B9E8", "#C9A7D6", "#D8CDB4", "#D99A2B",
    "#D9A15B", "#D9C36A", "#E6B3C3", "#F0B24A",
]  # fmt: skip

# --- Ingredient text -----------------------------------------------------------

GROUP_TEXT: dict[str | None, tuple[str, str, str]] = {
    "humectant": (
        "Humectant",
        "Pulls water into the hair.",
        "Keeps hair hydrated between washes.",
    ),
    "protein": (
        "Protein",
        "Fills in weak spots along the strand.",
        "Makes hair stronger and less likely to snap.",
    ),
    "butter": (
        "Butter",
        "Coats hair in a rich, soft layer.",
        "Locks moisture in and softens dry or thick hair.",
    ),
    "heavy_oil": (
        "Heavy oil",
        "Coats hair in a thick layer of oil.",
        "Seals moisture in and adds shine. Can weigh fine hair down.",
    ),
    "light_oil": (
        "Light oil",
        "Adds a thin layer of oil.",
        "Softens hair and adds shine without much weight.",
    ),
    "silicone_insoluble": (
        "Silicone",
        "Forms a smooth film that water alone doesn't rinse off.",
        "Cuts frizz and adds slip and shine. Can build up without a stronger shampoo.",
    ),
    "silicone_soluble": (
        "Water-soluble silicone",
        "Forms a light, smooth film that rinses off with water.",
        "Adds slip and shine with little build-up.",
    ),
    "fatty_alcohol": (
        "Fatty alcohol",
        "Thickens the formula and softens hair.",
        "Gives creams body and adds slip. It is not drying.",
    ),
    "drying_alcohol": (
        "Alcohol",
        "Evaporates quickly.",
        "Helps the product dry fast. Can dry hair out.",
    ),
    "sulfate": (
        "Cleanser",
        "Makes a strong lather that lifts oil and dirt.",
        "Cleans thoroughly. Can strip moisture from dry or curly hair.",
    ),
    "gentle_surfactant": (
        "Mild cleanser",
        "Lifts oil and dirt with a softer lather.",
        "Cleans without stripping as much moisture as sulfates.",
    ),
    "conditioning_agent": (
        "Conditioning agent",
        "Clings to hair and smooths it.",
        "Adds slip for detangling and cuts static.",
    ),
    "hold_polymer": (
        "Hold",
        "Forms a film that holds hair in shape.",
        "Keeps curls and styles in place.",
    ),
    "uv_filter": (
        "UV filter",
        "Absorbs sunlight.",
        "Helps protect hair and color from the sun.",
    ),
    "scalp_active": (
        "Scalp care",
        "Works on the scalp.",
        "Added to calm the scalp, fight flakes, or freshen it.",
    ),
    "starch": (
        "Starch",
        "Soaks up oil.",
        "Absorbs oil and adds texture or volume.",
    ),
    None: (
        "Other",
        "One of the formula's other ingredients.",
        "Not sorted into a group yet.",
    ),
}

# Common ingredients outside the hair groups whose job is well known.
ROLE_TEXT: list[tuple[str, tuple[str, str, str]]] = [
    (
        (
            r"phenoxyethanol|benzoate|sorbate|sorbic acid|paraben|isothiazolinone"
            r"|ethylhexylglycerin|caprylyl glycol|benzyl alcohol|dmdm hydantoin"
            r"|caprylhydroxamic|gluconolactone"
        ),
        ("Preservative", "Stops mold and bacteria.", "Keeps the product safe to use."),
    ),
    (
        (
            r"^(citric|lactic) acid$|sodium hydroxide|triethanolamine"
            r"|aminomethyl propanol|sodium citrate"
        ),
        ("pH adjuster", "Sets how acidic the product is.", "Keeps the formula stable."),
    ),
    (
        r"xanthan|\bgum\b|cellulose|carbomer|^sodium chloride$",
        ("Thickener", "Thickens the formula.", "Gives the product its texture."),
    ),
    (
        (
            r"^(limonene|linalool|geraniol|citronellol|coumarin|hexyl cinnamal"
            r"|benzyl salicylate|eugenol|citral|benzyl benzoate|alpha-isomethyl ionone)$"
        ),
        (
            "Scent",
            "Part of the scent.",
            "Listed by law because some people react to it.",
        ),
    ),
    (
        r"edta|phytate|ethylenediamine disuccinate",
        ("Chelator", "Binds minerals in water.", "Keeps the formula stable."),
    ),
    (
        r"^tocopher",
        ("Antioxidant", "Vitamin E.", "Keeps oils in the formula from going off."),
    ),
]

KNOWN: dict[str, tuple[str, str, str, str]] = {
    "water": (
        "Water",
        "Solvent",
        "The base that dissolves and carries everything else.",
        "Most hair products are mostly water. It spreads the rest evenly.",
    ),
    "fragrance": (
        "Fragrance",
        "Scent",
        "Gives the product its smell.",
        "Added for scent. Can bother sensitive scalps.",
    ),
    "glycerin": (
        "Glycerin",
        "Humectant",
        "Pulls water into the hair.",
        "Keeps hair hydrated between washes.",
    ),
}


def ingredient_record(key: str, inci: str) -> dict:
    if key in KNOWN:
        name, function, what, why = KNOWN[key]
    else:
        function, what, why = GROUP_TEXT[classify(inci)]
        if function == "Other":
            low = inci.lower()
            function, what, why = next(
                (text for pattern, text in ROLE_TEXT if re.search(pattern, low)),
                (function, what, why),
            )
        name = display_name(inci)
    return {
        "id": key,
        "name": name,
        "inci": inci,
        "function": function,
        "what_it_does": what,
        "why_its_added": why,
        "is_base": key == "water",
    }


# --- Hair types ----------------------------------------------------------------

FAMILY_CODES = {
    "straight": ["1A", "1B", "1C"],
    "wavy": ["2A", "2B", "2C"],
    "curly": ["3A", "3B", "3C"],
    "coily": ["4A", "4B", "4C"],
    "kinky": ["4A", "4B", "4C"],
}
CODE = r"[1-4][abc]"
# Not product numbers like Olaplex "Nº.4C" / "No. 4C".
CODE_LIST = re.compile(
    rf"(?<![º°.])(?<!no )\b{CODE}\b"
    rf"(?:\s*(?:,|/|&|and|or|-|–|—|to|through|thru)\s*{CODE}\b|[-–][abc]\b)*",
    re.IGNORECASE,
)
HAIR_WORD = re.compile(r"hair|curl|coil|texture|type|pattern", re.IGNORECASE)
FAMILY_LINE = re.compile(
    r"hair (?:type|pattern|texture)s?\s*:\s*([^\n.]*)", re.IGNORECASE
)
FAMILY_WORDS = r"straight|wavy|curly|coily|kinky"
FOR_FAMILIES = re.compile(
    rf"\bfor ((?:{FAMILY_WORDS})(?:\s*(?:,|and|or|&|/|to)\s*(?:{FAMILY_WORDS}))*),?"
    r"\s*(?:hair|curls|coils|textures?|types?)",
    re.IGNORECASE,
)


def _codes_in_list(text: str) -> set[str]:
    """ "3A-4C, 2b" → 3A..4C and 2B; "3A-C" → 3A..3C."""
    codes: set[str] = set()
    prev, ranging = None, False
    for part in re.findall(
        r"\b[1-4]?[abc]\b|[-–—]|\b(?:to|through|thru)\b", text, re.IGNORECASE
    ):
        if not re.fullmatch(r"[1-4]?[abc]", part, re.IGNORECASE):
            ranging = prev is not None
            continue
        if len(part) == 1 and prev is None:
            continue
        code = part.upper() if len(part) == 2 else prev[0] + part.upper()
        if ranging:
            lo, hi = sorted((HAIR_TYPES.index(prev), HAIR_TYPES.index(code)))
            codes.update(HAIR_TYPES[lo : hi + 1])
        codes.add(code)
        prev, ranging = code, False
    return codes


def hair_types_in(text: str) -> list[str]:
    """Hair types the product's own text names: "for 3A-4C hair", "Hair Pattern: Wavy, Curly"."""
    codes: set[str] = set()
    for m in CODE_LIST.finditer(text):
        nearby = text[max(0, m.start() - 25) : m.end() + 25]
        if HAIR_WORD.search(nearby):
            codes |= _codes_in_list(m.group(0))
    segments = [m.group(1) for m in FAMILY_LINE.finditer(text)]
    segments += [m.group(1) for m in FOR_FAMILIES.finditer(text)]
    for segment in segments:
        for word in re.findall(FAMILY_WORDS, segment, re.IGNORECASE):
            codes.update(FAMILY_CODES[word.lower()])
    return [c for c in HAIR_TYPES if c in codes]


# --- Products ------------------------------------------------------------------


def category_for(kind: str, text: str) -> str:
    t = text.lower()
    if kind == "shampoo":
        return "Co-wash" if re.search(r"co-?wash", t) else "Shampoo"
    if kind == "cream":
        if "butter" in t:
            return "Hair butter"
        if re.search(r"curl|coil|custard|defin", t):
            return "Curl cream"
        return "Styling cream"
    if kind == "serum":
        return "Scalp serum" if re.search(r"scalp|growth|regrowth", t) else "Hair serum"
    if kind == "spray":
        styling = r"hold|hair ?spray|texturi|sea salt|wave spray|finish|volumi"
        return "Styling spray" if re.search(styling, t) else "Treatment spray"
    return {
        "dry_shampoo": "Dry shampoo",
        "leave_in": "Leave-in conditioner",
        "edge_control": "Edge control",
        "deep_conditioner": "Deep conditioner",
        "conditioner": "Conditioner",
        "gel": "Gel",
        "mousse": "Mousse",
        "oil": "Hair oil",
    }[kind]


def short(text: str | None, limit: int) -> str:
    text = re.sub(r"[ \t]+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sentence = cut.rfind(". ")
    if sentence > limit // 2:
        return cut[: sentence + 1]
    return cut.rsplit(" ", 1)[0] + "…"


def clean_name(name: str, source: str) -> str:
    if source == "amazon_2023":
        # Amazon titles pile sizes and keywords after the name.
        head = re.split(r"\s[|–-]\s|,\s", name)[0].strip()
        name = head if len(head) >= 15 else name
    return short(name.strip(), 120)


def dedupe_key(brand: str, name: str) -> str:
    b = re.sub(r"[^a-z0-9]", "", brand.lower())
    n = re.sub(r"\([^)]*\)", " ", name.lower())
    n = re.sub(r"\b\d+(\.\d+)?\s*(fl\.?\s*oz|oz|ml|ounces?|l|g)\b.*", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    n = n.removeprefix(b)
    return f"{b}:{n}"


def read_source(source: str) -> list[dict]:
    """Every source as the common product record shape."""
    if source == "retail":
        rows = json.loads((DATA / "retail" / "products.json").read_text())
        return [
            {
                "source": "retail",
                "product_id": r["id"],
                "brand": r["brand"],
                "name": r["name"],
                "category": r["category"],
                "description": None,
                "ingredients_raw": r.get("ingredients"),
                "price_usd": r.get("sale_price_usd") or r.get("price_usd"),
                "size": r.get("size"),
                "url": r.get("url"),
                "image_url": None,
                "retailer": r.get("price_source"),
                "hair_text": "Hair type: "
                + ", ".join(r.get("marketing_hair_words") or []),
            }
            for r in rows
        ]
    rows = []
    with gzip.open(DATA / source / "products.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            r["source"] = source
            r["retailer"] = {"brands": r["brand"], "amazon_2023": "Amazon"}.get(source)
            amazon_type = (r.get("extra") or {}).get("hair_type")
            r["hair_text"] = f"Hair type: {amazon_type}" if amazon_type else ""
            rows.append(r)
    return rows


def build_product(r: dict, inci: list[str], kind: str) -> dict:
    pid = product_key(r["source"], r["product_id"])
    name = clean_name(r["name"], r["source"])
    text = f"{r['category']} {name}"
    description = short(r.get("description"), MAX_DESCRIPTION)
    listings = []
    if r.get("price_usd") and r.get("retailer") and r.get("url"):
        listings.append(
            {
                "retailer": r["retailer"],
                "price_usd": round(float(r["price_usd"]), 2),
                "size": r.get("size") or "",
                "url": r["url"],
            }
        )
    seen, formula = set(), []
    for name_ in inci:
        key = ingredient_key(name_)
        if key and key not in seen:
            seen.add(key)
            formula.append({"ingredient_id": key, "concentration_pct": None})
    return {
        "id": pid,
        "name": name,
        "brand": r["brand"] or "",
        "category": category_for(kind, text),
        "description": description,
        "hair_types": hair_types_in(f"{r.get('description') or ''}\n{r['hair_text']}"),
        "tags": [],
        "color": PALETTE[int(hashlib.md5(pid.encode()).hexdigest(), 16) % len(PALETTE)],
        "image_url": r.get("image_url"),
        "formula": formula,
        "listings": listings,
    }


def label_form(forms: Counter) -> str:
    """The most common spelling, avoiding ALL-CAPS labels when another one exists."""
    ranked = [form for form, _ in forms.most_common()]
    return next((f for f in ranked if not f.isupper()), ranked[0])


def main() -> None:
    seed = json.loads(SEED_PATH.read_text())
    products: dict[str, dict] = {}  # dedupe key → product
    inci_forms: dict[str, Counter] = {}
    survived: Counter = Counter()
    by_kind: Counter = Counter()
    dropped: Counter = Counter()
    for rank, source in enumerate(SOURCES):
        for r in read_source(source):
            if not r.get("ingredients_raw") or not r.get("name"):
                continue
            text = f"{r['category']} {r['name']}"
            if EXCLUDE.search(text):
                dropped[(source, "not a formula")] += 1
                continue
            kind = product_kind(r["name"], r["category"] or "")
            if kind == "other":
                dropped[(source, "kind other")] += 1
                continue
            inci = parse_inci(r["ingredients_raw"])
            if len({ingredient_key(i) for i in inci}) < MIN_INGREDIENTS:
                dropped[(source, "too few ingredients")] += 1
                continue
            product = build_product(r, inci, kind)
            key = dedupe_key(product["brand"], product["name"])
            held = products.get(key)
            if held is not None:
                # Same source twice: keep the fuller record.
                same = held["_rank"] == rank
                fuller = len(product["formula"]) > len(held["formula"])
                if not (same and fuller):
                    dropped[(source, "duplicate")] += 1
                    continue
                survived[held["_source"]] -= 1
                by_kind[(held["_source"], held["_kind"])] -= 1
            for name in inci:
                inci_forms.setdefault(ingredient_key(name), Counter())[name] += 1
            products[key] = {**product, "_rank": rank, "_source": source, "_kind": kind}
            survived[source] += 1
            by_kind[(source, kind)] += 1

    used = Counter(e["ingredient_id"] for p in products.values() for e in p["formula"])
    ingredients = [
        ingredient_record(key, label_form(inci_forms[key])) for key in sorted(used)
    ]
    out = {
        "hair_types": seed["hair_types"],
        "ingredients": ingredients,
        "products": [
            {k: v for k, v in p.items() if not k.startswith("_")}
            for p in products.values()
        ],
    }
    CatalogFile.model_validate(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    report(products, ingredients, used, survived, by_kind, dropped)


def report(products, ingredients, used, survived, by_kind, dropped) -> None:
    print(f"Wrote {OUT}: {len(products)} products, {len(ingredients)} ingredients")
    for source in SOURCES:
        kinds = {k: n for (s, k), n in sorted(by_kind.items()) if s == source and n}
        print(f"  {source}: {survived[source]} kept {kinds}")
        lost = {why: n for (s, why), n in dropped.items() if s == source}
        print(f"    dropped {lost}")
    print(
        "Per kind:", dict(Counter(p["_kind"] for p in products.values()).most_common())
    )
    with_types = sum(1 for p in products.values() if p["hair_types"])
    with_price = sum(1 for p in products.values() if p["listings"])
    print(f"With hair types: {with_types}; with a price: {with_price}")
    by_id = {i["id"]: i for i in ingredients}
    grouped = sum(n for k, n in used.items() if classify(by_id[k]["inci"]))
    other = sum(n for k, n in used.items() if by_id[k]["function"] == "Other")
    total = sum(used.values())
    print(
        f"Ingredient occurrences: {total}; with a group {grouped / total:.1%};"
        f" still 'Other' after role table {other / total:.1%}"
    )
    ungrouped = Counter(
        {
            by_id[k]["inci"]: n
            for k, n in used.items()
            if not classify(by_id[k]["inci"]) and k not in KNOWN
        }
    )
    print("Top ungrouped:", ungrouped.most_common(20))


if __name__ == "__main__":
    main()
