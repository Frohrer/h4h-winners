import { Link } from 'react-router-dom'
import type { ProductSummary } from '../types'
import { formatPrice } from '../format'
import { ProductImage } from './ProductImage'
import { FavoriteToggle } from './SaveButtons'

export function ProductTile({ product, reasons }: { product: ProductSummary; reasons?: string[] }) {
  return (
    <article className="tile">
      <div className="tile__media">
        <Link to={`/products/${product.id}`} tabIndex={-1} aria-hidden="true">
          <ProductImage product={product} />
        </Link>
        <FavoriteToggle productId={product.id} productName={product.name} />
      </div>
      <p className="tile__brand">{product.brand}</p>
      <h3 className="tile__name">
        <Link to={`/products/${product.id}`}>{product.name}</Link>
      </h3>
      <p className="tile__meta">
        {product.category}
        {product.price_from != null && <span className="tile__price">from {formatPrice(product.price_from)}</span>}
      </p>
      {reasons && reasons.length > 0 && (
        <ul className="reasons">
          {reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
    </article>
  )
}
