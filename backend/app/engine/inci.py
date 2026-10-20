"""Turns a printed ingredient label into an ordered list of INCI names.

Scraped labels are messy: headers ("INGREDIENTS/INGRÉDIENTS:"), batch codes
("1213537CD - Aqua/Water"), legal tails ("May contain", "F.I.L. D238909/1"),
footnotes ("*Certified organic"), bullets, and lists with no commas at all.
"""

import re

# Everything from here on is not an ingredient.
_TAIL = re.compile(
    r"\b(may contain|peut contenir|f\.i\.l\.|fil code|pat:|patents?\b|www\.|https?:|see more"
    r"|made in|distributed by|manufactured|imported by|fabriqu[ée]|hergestellt)"
    r"|\+/-|…|\(?\bfil\b[ .:]"
    # "Limonene*Natural component of...", "Linalool.*Certified organic"
    r"|(?<=[a-z).])\s*[*\\]+\s*(certified|natural|naturally|organic|plant|denotes|ingredients?)\b",
    re.IGNORECASE,
)
# "1213537CD - Aqua", "1166061 A - AQUA", "1101683ps10 aqua"
_BATCH_CODE = re.compile(
    r"^(?=[A-Z0-9]*\d)[A-Z0-9]{5,}\s+[-–]\s+|^(?=[a-z]*\d{4})[a-z0-9]{5,}(\s+[a-z]\b)?\s*[-–]?\s+",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"^\d+([.,]\d+)?\s*%\s*|\s*[-–]?\s*\d+([.,]\d+)?\s*%$")
# "Ingredients:", "Conditioner:", "Anwendung:" (but not "11:40")
_LABEL = re.compile(r"[^\W\d_]{3,}\s*:")
_ORGANIC_MARK = re.compile(r"^[*\\]+\s*organic\s+", re.IGNORECASE)


def _split_top_level(text: str) -> list[str]:
    """Splits on , and ; outside parentheses, so "Aqua (Water, Eau)" stays one name."""
    if text.count("(") != text.count(")"):
        return re.split(r"[,;]", text)
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in ",;" and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _looks_like_list(text: str) -> bool:
    """Several short comma-separated names, not marketing prose."""
    parts = re.split(r"[,;]", text)
    return len(parts) >= 5 and len(text) / len(parts) < 40


def _clean(token: str) -> str:
    token = _BATCH_CODE.sub("", token.strip().replace("\0", ","))
    token = _PERCENT.sub("", token)
    token = _ORGANIC_MARK.sub("", token)
    token = re.sub(r"[*\\]", "", token)
    return re.sub(r"\s+", " ", token).strip(" .-")


MARKETING = re.compile(r"\b(our|all-new|formula|contains|made with)\b", re.IGNORECASE)


def parse_inci(raw: str | None) -> list[str]:
    if not raw:
        return []
    text = re.sub(r"\s+", " ", raw)
    text = re.sub(r"[•·|]", ",", text)
    text = re.sub(r"\s\(and\)\s", ", ", text, flags=re.IGNORECASE)
    # "1,2-Hexanediol" is one name; restored in _clean.
    text = re.sub(r"(?<=\d),(?=\d)", "\0", text)
    tail = _TAIL.search(text)
    if tail:
        text = text[: tail.start()]
    # A "Word:" label before the list starts it; one after it (a second language,
    # a second product, directions) ends it.
    label = _LABEL.search(text)
    while label:
        if _looks_like_list(text[: label.start()]):
            text = text[: label.start()]
            break
        text = text[label.end() :]
        label = _LABEL.search(text)
    if len(re.findall(r"[,;]", text)) >= 3:
        tokens = _split_top_level(text)
    else:
        tokens = re.split(r"(?<=\))\s+", text)
    # Some labels end each name with a period instead of a comma.
    tokens = [t for token in tokens for t in re.split(r"\.\s+(?=[A-Za-z])", token)]
    out = []
    for token in map(_clean, tokens):
        # Long tokens and "Our all-new ... formula" are marketing, not names.
        prose = (
            len(token) > 100 or len(token.split()) > 10 or bool(MARKETING.search(token))
        )
        if re.search(r"[a-z]", token, re.IGNORECASE) and not prose:
            out.append(token)
    return out


_WATER = {"aqua", "water", "eau", "agua", "acqua", "purified", "deionized", "distilled"}
_FRAGRANCE = {"fragrance", "parfum", "perfume", "aroma"}


def _is_only(words: list[str], allowed: set[str], core: set[str]) -> bool:
    return bool(words) and set(words) <= allowed and bool(set(words) & core)


def ingredient_key(inci: str) -> str:
    """One id per ingredient across labels: "Aqua/Water/Eau" and "Water (Aqua)" → "water"."""
    name = re.sub(r"\s+", " ", inci.lower()).strip(" .")
    words = re.sub(r"[()/,\[\]]", " ", name).split()
    if _is_only(words, _WATER, {"aqua", "water", "eau"}):
        return "water"
    if _is_only(words, _FRAGRANCE, {"fragrance", "parfum"}):
        return "fragrance"
    if _is_only(
        words, {"glycerin", "glycerine", "vegetable"}, {"glycerin", "glycerine"}
    ):
        return "glycerin"
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def _sentence_case(text: str) -> str:
    if text.isupper():
        text = text.lower()
    words = [
        w if w.isupper() or re.search(r"\d", w) else w.lower() for w in text.split()
    ]
    out = " ".join(words)
    return out[:1].upper() + out[1:]


def display_name(inci: str) -> str:
    """A readable name: "Butyrospermum Parkii (Shea) Butter" → "Shea butter"."""
    # Only for a two-word Latin plant name, so "Hydrolyzed ... (Baobab) Protein" keeps its INCI.
    common = re.fullmatch(r"[A-Za-z-]+ [A-Za-z-]+ \(([^()]+)\) ([^()]+)", inci.strip())
    if common:
        return _sentence_case(f"{common.group(1)} {common.group(2)}")
    return _sentence_case(inci.strip())
