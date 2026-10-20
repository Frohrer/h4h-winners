import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

// PLACEHOLDERS until the scrape lands. Replace with real figures, ideally
// served from an /api/stats endpoint so this page can't drift from the data.
// Everything rendered through <Ph> gets a dashed underline so placeholder
// copy is obvious in demos and easy to find when swapping in real numbers.
const STATS = {
  products: 'XX,XXX',
  brands: 'X,XXX',
  reviews: 'X,XXX,XXX',
  ingredients: 'X,XXX',
  refreshDays: 'X',
}

const RELEASE = {
  formats: 'CSV and JSON',
  license: 'License to be announced',
  date: 'Release date to be announced',
  contact: 'data@example.com',
}

// Matches scraper/README.md: open datasets and public brand endpoints only,
// no retailer scraping. Keep this list in step with what scraper/ really collects.
const SOURCES = [
  {
    kind: 'Open datasets',
    count: 'XX datasets',
    takes: 'Ingredient lists from Open Beauty Facts, and ratings and reviews from the Amazon Reviews 2023 research dataset',
  },
  {
    kind: 'Brand websites',
    count: 'X,XXX brands',
    takes: 'Product details, full ingredient lists, prices, and reviews from each brand’s public product pages',
  },
  {
    kind: 'Ingredient references',
    count: 'XX sources',
    takes: 'What each ingredient does and why formulators add it',
  },
]

const SIGNALS = [
  {
    name: 'Your hair type',
    body: 'The textures you pick, from 1A to 4C. Products are matched to the hair types they’re made for, and you can pick more than one.',
  },
  {
    name: 'Products that already work for you',
    body: 'Favorites and the products you use now. We look for formulas close to them, compared ingredient by ingredient and by how much of each they contain.',
  },
  {
    name: 'What you ask for',
    body: 'Your own words, like “less shrinkage”, “lightweight moisture”, or “something for my edges”.',
  },
  {
    name: 'Where you are',
    body: 'Today’s humidity and dew point near you. Humid air calls for more hold, and dry air calls for more sealing. You can change or remove your location at any time.',
  },
  {
    name: 'What’s in the bottle',
    body: 'Every ingredient on the label, what it does, and an estimate of how much the product contains.',
  },
  {
    name: 'What people say',
    body: 'Ratings and reviews from people who have used each product, so a formula that looks right on paper also has to work in practice.',
  },
  {
    name: 'What it costs',
    body: 'Prices and sizes, so you can compare price per ounce, not just the sticker.',
  },
]

// Mirrors the real catalog record shape (backend/app/models.py: Product), trimmed.
const SAMPLE = `{
  "name": "Whipped Shea Curl Cream",
  "brand": "Coilwell",
  "category": "Curl cream",
  "hair_types": ["3C", "4A", "4B", "4C"],
  "formula": [
    { "ingredient": "Water", "concentration_pct": 56 },
    { "ingredient": "Shea butter", "concentration_pct": 12 },
    { "ingredient": "Aloe vera juice", "concentration_pct": 8 },
    …
  ],
  "listings": [
    { "retailer": "Strand Supply", "price_usd": 15.49, "size": "8 oz" },
    …
  ]
}`

function Ph({ children }: { children: ReactNode }) {
  return (
    <span className="placeholder" title="Placeholder">
      {children}
    </span>
  )
}

export function DataPage() {
  return (
    <article className="data">
      <header className="data__hero">
        <h1 className="display">Every recommendation starts with the label.</h1>
        <p className="data__lead">
          Strand reads the ingredient lists of <Ph>{STATS.products}</Ph> hair products from <Ph>{STATS.brands}</Ph>{' '}
          brands, learns from <Ph>{STATS.reviews}</Ph> reviews, and explains <Ph>{STATS.ingredients}</Ph> ingredients
          in plain language.
        </p>
      </header>

      <section className="data__section" aria-labelledby="signals-heading">
        <h2 id="signals-heading">What goes into a recommendation</h2>
        <dl className="signals">
          {SIGNALS.map((s) => (
            <div key={s.name}>
              <dt>{s.name}</dt>
              <dd>{s.body}</dd>
            </div>
          ))}
        </dl>
        <p className="data__aside">
          Every result shows the reasons it was picked, so you can see which of these mattered.{' '}
          <Link to="/">Try it</Link>
        </p>
      </section>

      <section className="data__section" aria-labelledby="sources-heading">
        <h2 id="sources-heading">Where it comes from</h2>
        <p className="data__body">
          We combine open research datasets with the public product pages brands publish themselves. We don’t scrape
          stores whose terms forbid it, and we never keep reviewers’ names. The catalog refreshes every{' '}
          <Ph>{STATS.refreshDays}</Ph> days, so formulas stay current when brands reformulate.
        </p>
        <table className="sources">
          <thead className="visually-hidden">
            <tr>
              <th>Source</th>
              <th>What we take</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map((s) => (
              <tr key={s.kind}>
                <th scope="row">
                  {s.kind}
                  <span className="muted">
                    <Ph>{s.count}</Ph>
                  </span>
                </th>
                <td>{s.takes}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h3>What we estimate</h3>
        <p className="data__body">
          Brands rarely publish exact percentages. Labels list ingredients from most to least, so we estimate each
          concentration from its position and mark it as an estimate wherever a number appears.
        </p>
      </section>

      <section className="data__section data__open" aria-labelledby="open-heading">
        <div>
          <h2 id="open-heading">The full dataset will be free</h2>
          <p className="data__body">
            When the collection is complete, we’ll publish all of it for anyone to download: products, full ingredient
            lists, estimated concentrations, prices, reviews, and ingredient explanations. It’s for researchers, brands,
            and anyone building something for people with textured hair.
          </p>
          <dl className="release">
            <div>
              <dt>Formats</dt>
              <dd>
                <Ph>{RELEASE.formats}</Ph>
              </dd>
            </div>
            <div>
              <dt>License</dt>
              <dd>
                <Ph>{RELEASE.license}</Ph>
              </dd>
            </div>
            <div>
              <dt>Available</dt>
              <dd>
                <Ph>{RELEASE.date}</Ph>
              </dd>
            </div>
          </dl>
          <a className="button button--primary" href={`mailto:${RELEASE.contact}?subject=Strand%20dataset`}>
            Ask for early access
          </a>
        </div>
        <figure className="sample">
          <figcaption>One product record</figcaption>
          <pre>
            <code>{SAMPLE}</code>
          </pre>
        </figure>
      </section>
    </article>
  )
}
