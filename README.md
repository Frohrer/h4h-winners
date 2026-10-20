# Strand

Hair product recommendations by hair type (1A–4C), the products you already like, what you're looking for, and the weather where you are. Every product page shows where it's sold, its full ingredient list with what each ingredient does, products with similar formulas, and similar products.

The catalog is **fictional seed data** for now (`backend/app/data/catalog.json`), and recommendations come from a deliberately naive stub until the real recommender is ready.

| Directory | What it is |
|---|---|
| `frontend/` | React + Vite + TypeScript UI |
| `backend/` | FastAPI app: catalog, recommender interface, location + weather |
| `scraper/` | Data collection into `data/` (see `scraper/README.md`) |

## Run it

Two terminals:

```sh
cd backend && uv run fastapi dev app/main.py     # API on :8000
cd frontend && npm install && npm run dev        # UI on http://localhost:5173
```

Vite proxies `/api` to the backend, so open the UI on port 5173 only.

Tests and lint:

```sh
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && npm run build && npm run lint
```

## Plugging in the real recommender

Implement the `Recommender` protocol in `backend/app/recommender.py` (two methods: `recommend` for the finder, and `similar_products`, which ranks by formula similarity, meaning shared ingredients weighted by concentration) and return it from `get_recommender()`. Routes, the UI, and the API contract stay the same. Each `recommend` call receives:

- `hair_types`, `liked_product_ids`, `current_product_ids`, and free-text `query`
- `location` (or `null` if the person turned it off)
- `environment`: current temperature, humidity, and dew point at that location, looked up by the API before calling you

Return `reasons` with each result. The UI shows them under every product so people can see why it was suggested.

To swap the seed catalog for scraped data, replace `load_catalog()` in `backend/app/catalog.py` with a source that produces the same `Product` / `Ingredient` records (`backend/app/models.py`).

## Location and weather

On first visit the UI asks `/api/location`, which looks up the visitor's IP with [ipwho.is](https://ipwho.is). In local dev that resolves to your own public IP. People can change the city (search runs through Open-Meteo geocoding) or turn location off; the choice is stored in their browser and never re-detected over. Weather comes from [Open-Meteo](https://open-meteo.com). Both are free and keyless, but ipwho.is receives every visitor's IP, so once deployed behind Cloudflare, Vercel, or CloudFront, switch `get_location_service()` to read the edge's geo headers instead.

## Profiles

Hair types, favorites, products in use, and location live in `localStorage` (no accounts yet) and are sent in full with each recommendation request, so moving them server-side later doesn't change the API.
