import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

// Rounded down from the first full scrape (data/*/MANIFEST.json). Rounded on
// purpose: counts move with every refresh, and the page shouldn't promise more
// precision than a snapshot has. Ideally served from /api/stats later.
// Brands stays vague because marketplace seller names inflate the raw count.
// Sources are described by kind, not by name, by request.
const STATS = {
  reviews: '3 million',
  products: '100,000',
  brands: 'thousands of',
  hairProfileReviews: '350,000',
  ingredientLists: '2,800',
  communityPosts: '130,000',
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
    kind: 'Open research datasets',
    count: 'Millions of reviews',
    takes: 'Product ratings and reviews published for research, plus ingredient lists from an open product database',
  },
  {
    kind: 'Brand websites',
    count: 'About 80 brands',
    takes: 'Product details, ingredient lists, prices, and reviews from brands’ own public product pages, including the hair type, porosity, and thickness reviewers report',
  },
  {
    kind: 'Hair-care communities',
    count: `${STATS.communityPosts}+ posts`,
    takes: 'Public discussions where people describe their hair and what has and hasn’t worked for it',
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
    body: 'Ratings and reviews from people who have used each product, so a formula that looks right on paper also has to work in practice. Many reviewers describe their own hair, so we can see how a product does on hair like yours.',
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
    { "ingredient": "Water" },
    { "ingredient": "Shea butter" },
    { "ingredient": "Aloe vera juice" },
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
          strands.hair learns from over {STATS.reviews} reviews of more than {STATS.products} hair products from{' '}
          {STATS.brands} brands. In over {STATS.hairProfileReviews} of them, the reviewer tells us about their own hair:
          its type, porosity, or thickness.
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
          We combine open research datasets, public hair-care communities, and the product pages brands publish
          themselves. We don’t scrape stores whose terms forbid it, and we never keep reviewers’ names. Full ingredient
          lists cover {STATS.ingredientLists}+ products so far, and that number grows as we add brands.
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
                  <span className="muted">{s.count}</span>
                </th>
                <td>{s.takes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="data__section data__open" aria-labelledby="open-heading">
        <div>
          <h2 id="open-heading">The full dataset will be free</h2>
          <p className="data__body">
            When the collection is complete, we’ll publish all of it for anyone to download: products, full ingredient
            lists, prices, reviews, and ingredient explanations. It’s for researchers, brands,
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
          <a className="button button--primary" href={`mailto:${RELEASE.contact}?subject=strands.hair%20dataset`}>
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
