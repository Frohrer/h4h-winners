"""Tests run against the seed data, not the generated files docker-compose points at."""

import os

for var in ("STRAND_CATALOG", "STRAND_REVIEWS"):
    os.environ.pop(var, None)
