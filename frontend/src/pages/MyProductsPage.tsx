import { Link } from 'react-router-dom'
import { api } from '../api'
import { ProductImage } from '../components/ProductImage'
import { formatList } from '../format'
import { useProfile } from '../profile'
import type { ProductSummary } from '../types'
import { useAsync } from '../useAsync'

export function MyProductsPage() {
  const profile = useProfile()
  const ids = [...new Set([...profile.using, ...profile.favorites])]
  const products = useAsync(() => api.productsByIds(ids), [ids.join(',')])
  const byId = new Map(products.data?.map((p) => [p.id, p]))
  const resolve = (list: string[]) => list.map((id) => byId.get(id)).filter((p): p is ProductSummary => !!p)

  return (
    <div className="mine">
      <h1>My products</h1>
      <p className="mine__summary">
        {profile.hairTypes.length ? (
          <>
            Your hair type is <strong>{formatList(profile.hairTypes)}</strong>.{' '}
          </>
        ) : (
          'You haven’t picked a hair type yet. '
        )}
        <Link to="/">{profile.hairTypes.length ? 'Change it' : 'Pick one'}</Link>
      </p>

      <ProductList
        title="Using now"
        products={resolve(profile.using)}
        empty="Tap “I use this” on any product page to build your routine here."
        removeLabel="Remove from routine"
        onRemove={(id) => profile.toggle('using', id)}
      />
      <ProductList
        title="Favorites"
        products={resolve(profile.favorites)}
        empty="Tap the heart on any product to save it here."
        removeLabel="Remove from favorites"
        onRemove={(id) => profile.toggle('favorites', id)}
      />
    </div>
  )
}

interface ListProps {
  title: string
  products: ProductSummary[]
  empty: string
  removeLabel: string
  onRemove: (id: string) => void
}

function ProductList({ title, products, empty, removeLabel, onRemove }: ListProps) {
  return (
    <section className="mine__section">
      <h2>
        {title} <span className="count">{products.length}</span>
      </h2>
      {products.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul className="rows">
          {products.map((p) => (
            <li key={p.id} className="row">
              <Link to={`/products/${p.id}`} className="row__link">
                <ProductImage product={p} className="product-image--thumb" />
                <span>
                  <span className="row__name">{p.name}</span>
                  <span className="muted">
                    {p.brand}, {p.category.toLowerCase()}
                  </span>
                </span>
              </Link>
              <button type="button" className="link-button" onClick={() => onRemove(p.id)}>
                {removeLabel}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
