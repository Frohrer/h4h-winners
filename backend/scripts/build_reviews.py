"""Turn the scraped reviews in /data into review signals: /data/generated/reviews.jsonl.

    uv run --frozen python scripts/build_reviews.py [--data /data]

Streams every source line by line (the inputs are ~650 MB gzipped). Keeps reviews
that say something about the writer's hair (code, family, porosity or thickness),
the same rule combined/reviews_with_hair_profile uses, and that have a rating.
Sources:
- combined/reviews_with_hair_profile: Amazon 2023 (+ Reddit posts that name a product).
- brands/ and bazaarvoice/: brand-site widgets; structured answers in hair_profile.
- retail/reviews.csv: Ulta/Walmart, no text, tagged themes instead.
influenster_2017/ is skipped (licence caveat in data/README.md).
"""

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

# Run as a file from backend/, so make the app package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.review_text import read_review
from app.engine.reviews import ReviewSignal
from app.engine.vocab import HAIR_TYPES
from app.ids import product_key

THICKNESS = {"fine": "fine", "thin": "fine", "medium": "medium"}
THICKNESS |= {"thick": "coarse", "coarse": "coarse"}
FAMILIES = ["Straight", "Wavy", "Curly", "Coily"]
# Codes further apart than this are two people or a very mixed head ("I'm 4A, my
# daughter 3B"): no single code, fall back to the family if there is one.
MAX_CODE_SPREAD = 2

RETAIL_FAMILY = {"Straight Hair": "Straight", "Wavy Hair": "Wavy"}
RETAIL_FAMILY |= {"Very Curly Hair": "Curly"}
# fmt: off
RETAIL_HELPED = {
    "moisturizing": "moisture", "detangling": "detangle", "definition": "definition",
    "frizz_control": "frizz_control", "shine": "smoothness", "volume": "volume",
    "lightweight": "lightweight", "no_buildup": "lightweight", "strength": "protein",
    "no_flaking": "scalp_care", "no_irritation": "scalp_care",
}
RETAIL_HURT = {
    "dry": "moisture", "greasy": "lightweight", "buildup": "lightweight",
    "sticky": "lightweight", "frizz_complaint": "frizz_control", "crunchy": "smoothness",
    "flaking": "scalp_care", "scalp_irritation": "scalp_care",
}
# fmt: on

Rows = Iterator[tuple[str, dict | None]]  # (source, signal or None)


def one(values: list[str], mapping: dict[str, str] | None = None) -> str | None:
    """The value when exactly one is given (after mapping synonyms), else None."""
    mapped = {mapping.get(v) if mapping else v for v in values} - {None}
    return mapped.pop() if len(mapped) == 1 else None


def pick_code(codes: list[str]) -> str | None:
    """The first code, when all codes are within MAX_CODE_SPREAD steps ("3B/3C" → 3B)."""
    codes = [c.upper() for c in codes if c.upper() in HAIR_TYPES]
    if not codes:
        return None
    idx = [HAIR_TYPES.index(c) for c in codes]
    return codes[0] if max(idx) - min(idx) <= MAX_CODE_SPREAD else None


def sentiment_of(rating) -> float | None:
    if rating in (None, ""):
        return None
    return max(-1.0, min(1.0, (float(rating) - 3) / 2))


def signal(
    product_id: str,
    sentiment: float,
    codes: list[str],
    families: list[str],
    porosity: list[str],
    thickness: list[str],
    text: str,
    url: str | None,
) -> dict | None:
    hair_type = pick_code(codes)
    family = None if hair_type else one([f for f in families if f in FAMILIES])
    s = {
        "product_id": product_id,
        "hair_type": hair_type,
        "hair_family": family,
        "porosity": one(porosity),
        "thickness": one(thickness, THICKNESS),
        "sentiment": round(sentiment, 3),
    }
    if not any(s[k] for k in ("hair_type", "hair_family", "porosity", "thickness")):
        return None
    t = read_review(text, sentiment)
    s |= {"helped": t.helped, "hurt": t.hurt, "quote": t.quote, "climate": t.climate}
    s["source_url"] = url
    return s


def gz_rows(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt") as f:
        for line in f:
            yield json.loads(line)


def text_of(row: dict) -> str:
    return " ".join(p.strip() for p in (row.get("title"), row.get("text")) if p)


def combined(data: Path, stats: Counter) -> Rows:
    """Amazon + Reddit; hair fields are all parsed from the text (hair_source=text)."""
    for row in gz_rows(data / "combined" / "reviews_with_hair_profile.jsonl.gz"):
        src = row["source"]
        stats[f"{src}:read"] += 1
        sentiment = sentiment_of(row.get("rating"))
        if not row.get("product_id") or sentiment is None:
            continue
        yield (
            src,
            signal(
                product_key(src, row["product_id"]),
                sentiment,
                row["hair_types"],
                row["hair_families"],
                row["porosity"],
                row["thickness"],
                text_of(row),
                row.get("url"),
            ),
        )


def from_profile(values: list[str], profile: dict) -> list[str]:
    """The values a structured answer states ("Hair Type: Thick Hair, Curly Hair").

    Text-derived values are a fallback: they can describe advice to others."""
    answers = " ".join(str(v) for v in profile.values()).lower()
    # Bazaarvoice answers are CamelCase ids ("Type3Curly"), hence no leading \b.
    return [v for v in values if re.search(rf"{v.lower()}\b", answers)]


def widgets(data: Path, stats: Counter) -> Rows:
    """brands/ and bazaarvoice/: structured answers first, then the text parse."""
    for folder in ("brands", "bazaarvoice"):
        for row in gz_rows(data / folder / "reviews.jsonl.gz"):
            src = row["source"]
            stats[f"{src}:read"] += 1
            sentiment = sentiment_of(row.get("rating"))
            if not row.get("product_id") or sentiment is None:
                continue
            profile = row.get("hair_profile") or {}
            fields = {}
            for key in ("hair_families", "porosity", "thickness"):
                stated = from_profile(row[key], profile)
                fields[key] = stated or row[key]
            yield (
                src,
                signal(
                    product_key(src, row["product_id"]),
                    sentiment,
                    row["hair_types"] or row["hair_types_from_text"],
                    fields["hair_families"],
                    fields["porosity"],
                    fields["thickness"],
                    text_of(row),
                    row.get("url"),
                ),
            )


def cells(value: str) -> list[str]:
    """A "|"-joined CSV cell as its values: "3A|3B" → ["3A", "3B"]."""
    return [v for v in value.split("|") if v]


def needs_from_themes(themes: list[str], mapping: dict[str, str]) -> list[str]:
    return list(dict.fromkeys(mapping[t] for t in themes if t in mapping))


def retail_signal(row: dict, sentiment: float) -> dict | None:
    family = RETAIL_FAMILY.get(row["retailer_hair_type"])
    family = family or row["texture_best"].capitalize()
    s = signal(
        product_key("retail", row["product_id"]),
        sentiment,
        cells(row["curl_patterns"]),
        [family],
        cells(row["porosity"]),
        cells(row["thickness"]),
        "",
        row["review_url"] or None,
    )
    if s:
        themes = cells(row["themes"])
        s["helped"] = needs_from_themes(themes, RETAIL_HELPED)
        s["hurt"] = needs_from_themes(themes, RETAIL_HURT)
    return s


def retail(data: Path, stats: Counter) -> Rows:
    """Ulta/Walmart: no text, so needs come from the tagged themes."""
    with (data / "retail" / "reviews.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            stats["retail:read"] += 1
            sentiment = sentiment_of(row["rating"])
            if row["repeated_text"] == "True" or sentiment is None:
                continue
            yield "retail", retail_signal(row, sentiment)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("/data"))
    args = parser.parse_args()
    out = args.data / "generated" / "reviews.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    stats: Counter = Counter()
    tmp = out.with_suffix(".jsonl.tmp")
    with tmp.open("w") as f:
        for source in (combined, widgets, retail):
            for src, s in source(args.data, stats):
                if s is None:
                    continue
                # Validate here so the app can trust every line it loads.
                line = ReviewSignal.model_validate(s).model_dump_json(
                    exclude_defaults=True
                )
                f.write(line + "\n")
                stats[f"{src}:written"] += 1
    tmp.replace(out)

    for key in sorted(stats):
        print(f"{key:>24} {stats[key]:>8}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
