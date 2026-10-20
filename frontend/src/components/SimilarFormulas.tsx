import { Link } from 'react-router-dom'
import type { SimilarFormula } from '../types'
import { formatPct } from '../format'
import { ProductImage } from './ProductImage'

const SHOWN_INGREDIENTS = 4

export function SimilarFormulas({ items, thisName }: { items: SimilarFormula[]; thisName: string }) {
  if (items.length === 0) {
    return <p className="muted">No other product shares enough ingredients with this one.</p>
  }
  return (
    <ul className="formulas">
      {items.map(({ product, similarity, shared }) => (
        <li key={product.id} className="formula">
          <Link to={`/products/${product.id}`} className="formula__head">
            <ProductImage product={product} className="product-image--thumb" />
            <span>
              <span className="formula__name">{product.name}</span>
              <span className="muted">
                {product.brand}, {product.category.toLowerCase()}
              </span>
            </span>
            <span className="formula__match">{Math.round(similarity * 100)}% match</span>
          </Link>
          <table className="compare">
            <thead>
              <tr>
                <th scope="col">Shared ingredient</th>
                <th scope="col" title={thisName}>
                  This product
                </th>
                <th scope="col" title={product.name}>
                  {product.name}
                </th>
              </tr>
            </thead>
            <tbody>
              {shared.slice(0, SHOWN_INGREDIENTS).map((s) => (
                <tr key={s.ingredient_id}>
                  <th scope="row">{s.name}</th>
                  <td>{formatPct(s.this_pct)}</td>
                  <td>{formatPct(s.other_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {shared.length > SHOWN_INGREDIENTS && (
            <p className="footnote">
              {shared.length - SHOWN_INGREDIENTS} more shared ingredient{shared.length - SHOWN_INGREDIENTS > 1 ? 's' : ''}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
