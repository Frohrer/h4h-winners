"""One rule for product ids, shared by the catalog builder and the review builder,
so a review's product_id always matches a catalog product's id."""

import re


def product_key(source: str, product_id: str) -> str:
    """("amazon_2023", "B0BWNHG7MX") → "amazon-2023-b0bwnhg7mx"."""
    return re.sub(r"[^a-z0-9]+", "-", f"{source}-{product_id}".lower()).strip("-")
