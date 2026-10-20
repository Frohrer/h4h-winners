"""The recommendation engine: hair + today + weather → needs → ingredient groups → products.

Everything hair-specific lives in rules.py and ingredient_groups.py; the rest is
plumbing that turns those tables into scores and plain-language reasons.
"""
