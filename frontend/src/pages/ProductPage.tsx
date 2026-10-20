import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { IngredientList } from '../components/IngredientList'
import { ProductImage } from '../components/ProductImage'
import { SaveButtons } from '../components/SaveButtons'
import { SimilarProducts } from '../components/SimilarProducts'
import { WhereToBuy } from '../components/WhereToBuy'
import { useProfile } from '../profileContext'
import { useAsync } from '../useAsync'
import { ApiDown } from './FinderPage'

export function ProductPage() {
  const { id = '' } = useParams()
  const profile = useProfile()
  const navigate = useNavigate()
  const routerLocation = useLocation()

  const product = useAsync(() => api.product(id), [id])
  const similar = useAsync(() => api.similarProducts(id), [id])

  // Clicking a similar product swaps the page in place; start it at the top.
  // Block body matters: Chrome's scrollTo returns a Promise, and React would
  // try to call it as the effect's cleanup and crash the page.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [id])

  if (product.error) {
    return product.error instanceof ApiError && product.error.status === 404 ? (
      <div className="empty">
        <h1>This product isn't in the catalog</h1>
        <Link to="/" className="button">
          Find products
        </Link>
      </div>
    ) : (
      <ApiDown />
    )
  }

  const p = product.data
  if (!p) return <div className="product product--loading" aria-busy="true" />

  // The initial entry has key "default": nothing to go back to inside the app.
  const canGoBack = routerLocation.key !== 'default'

  return (
    <article className="product">
      {canGoBack ? (
        <button type="button" className="link-button back" onClick={() => navigate(-1)}>
          Back
        </button>
      ) : (
        <Link to="/" className="back">
          Find products
        </Link>
      )}

      <div className="product__hero">
        <ProductImage product={p} className="product-image--large" />
        <div className="product__info">
          <p className="product__brand">{p.brand}</p>
          <h1 className="product__name">{p.name}</h1>
          <p className="muted">{p.category}</p>

          {p.hair_types.length > 0 && (
            <div className="product__types">
              <span className="muted">Made for</span>
              <ul className="type-list">
                {p.hair_types.map((code) => (
                  <li key={code} className={profile.hairTypes.includes(code) ? 'is-yours' : undefined}>
                    {code}
                    {profile.hairTypes.includes(code) && <span className="visually-hidden"> (your hair type)</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {p.description && <p className="product__description">{p.description}</p>}
          <SaveButtons productId={p.id} />

          <section className="product__section" aria-labelledby="buy-heading">
            <h2 id="buy-heading">Where to buy</h2>
            <WhereToBuy listings={p.listings} />
          </section>
        </div>
      </div>

      <section className="product__section" aria-labelledby="ingredients-heading">
        <h2 id="ingredients-heading">
          Ingredients <span className="count">{p.formula.length}</span>
        </h2>
        <IngredientList formula={p.formula} />
      </section>

      <section className="product__section" aria-labelledby="similar-heading">
        <h2 id="similar-heading">Similar products</h2>
        {similar.data && <SimilarProducts items={similar.data} />}
      </section>
    </article>
  )
}
