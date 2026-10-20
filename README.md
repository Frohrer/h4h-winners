# Strand

Hair product recommendations by hair type (1A–4C), the products you already like, what you're looking for, and the weather where you are. Every product page shows where it's sold, its full ingredient list with what each ingredient does, products with similar formulas, and similar products.

Without the scraped data the app runs on a small **fictional seed catalog** (`backend/app/data/catalog.json`). With it, the catalog and review signals are built from real products and reviews (see [Data](#data)).

| Directory | What it is |
|---|---|
| `frontend/` | React + Vite + TypeScript UI |
| `backend/` | FastAPI app: catalog, recommender, location + weather |
| `backend/app/engine/` | The recommendation engine and its rule tables |
| `backend/scripts/` | Build the catalog and review signals from `data/` |

## Run it

Everything runs in Docker:

```sh
docker compose up --build     # UI on http://localhost:5173, API on :8000
```

Vite proxies `/api` to the backend, so open the UI on port 5173 only.

Tests and lint:

```sh
docker compose run --rm --no-deps backend sh -c 'uv run pytest && uv run ruff check . && uv run ruff format --check .'
docker compose run --rm --no-deps frontend sh -c 'npm run build && npm run lint'
```

## How recommendations work

```
hair types, porosity, strands ─┐
what you typed                 ├─▶ needs ─▶ ingredient groups ─▶ products
today's weather                ┘                                   ▲
                       reviews from people with similar hair ──────┘
```

1. **Needs.** Hair type, porosity, strand thickness, the search text ("wash day", "defined curls") and the weather each add weight to needs like `moisture`, `seal` or `frizz_control` (`app/engine/rules.py`, tables A and B).
2. **Ingredients.** Every ingredient is sorted into one of 16 groups by its INCI name (`app/engine/ingredient_groups.py`): humectants, butters, rich oils, light oils, proteins, hold polymers, strong and gentle soaps, silicones, and so on. Bigger amounts count more; without percentages, earlier on the label counts more.
3. **Score.** Each group helps or hurts certain needs (table C). Weather changes some of that: glycerin causes frizz in humid air and dries hair out in very dry air.
4. **Reviews.** Reviews from people with the same hair type count fully, a neighbouring type or the same family (curly, coily) counts less, and a handful barely counts while dozens count a lot.
5. **Reasons.** Each result says why in plain words ("Shea butter and castor oil lock moisture in for today's dry air") and warns about what to watch out for ("Glycerin can cause frizz in today's humid air").

`GraphRecommender` in `backend/app/recommender.py` implements the `Recommender` protocol, so routes and the UI don't depend on how it works.

## Data

The scraped products and reviews are third-party content and are **not in this repo**. Put them in `data/` at the repo root (git-ignored), with the retail reviews in `data/retail/`.

Then build the catalog and review signals (written to `data/generated/`, which the backend loads at start):

```sh
docker compose run --rm --no-deps backend uv run python scripts/build_catalog.py
docker compose run --rm --no-deps backend uv run python scripts/build_reviews.py
docker compose up
```

## Location and weather

On first visit the UI asks `/api/location`, which looks up the visitor's IP with [ipwho.is](https://ipwho.is). In local dev that resolves to your own public IP. People can change the city (search runs through Open-Meteo geocoding) or turn location off; the choice is stored in their browser and never re-detected over. Weather comes from [Open-Meteo](https://open-meteo.com). Both are free and keyless, but ipwho.is receives every visitor's IP, so once deployed behind Cloudflare, Vercel, or CloudFront, switch `get_location_service()` to read the edge's geo headers instead.

## Profiles

Hair types, favorites, products in use, and location live in `localStorage` (no accounts yet) and are sent in full with each recommendation request, so moving them server-side later doesn't change the API.
