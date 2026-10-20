import type { SimilarProduct } from '../types'
import { formatPct } from '../format'
import { ProductTile } from './ProductTile'

const SHOWN_INGREDIENTS = 3

export function SimilarProducts({ items }: { items: SimilarProduct[] }) {
  if (items.length === 0) {
    return <p className="muted">No other product shares enough ingredients with this one yet.</p>
  }
  return (
    <div className="grid grid--similar">
      {items.map(({ product, similarity, shared }) => {
        const more = shared.length - SHOWN_INGREDIENTS
        return (
          <ProductTile key={product.id} product={product}>
            <div className="match">
              <p className="match__score">{Math.round(similarity * 100)}% formula match</p>
              <table className="compare">
                <caption className="visually-hidden">Shared ingredients with {product.name}</caption>
                <thead>
                  <tr>
                    <th scope="col">In both</th>
                    <th scope="col">This one</th>
                    <th scope="col">That one</th>
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
              {more > 0 && (
                <p className="footnote">
                  {more} more ingredient{more > 1 ? 's' : ''} in common
                </p>
              )}
            </div>
          </ProductTile>
        )
      })}
    </div>
  )
}
