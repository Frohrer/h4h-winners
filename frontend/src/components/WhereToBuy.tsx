import type { Listing } from '../types'
import { formatPrice } from '../format'

function perOunce(listing: Listing): number | null {
  const m = listing.size.match(/^([\d.]+)\s*oz$/i)
  return m ? listing.price_usd / Number(m[1]) : null
}

// Listings arrive sorted by sticker price, but the cheapest sticker can be the
// smaller bottle. "Best value" goes to the lowest price per ounce when every
// size parses, and falls back to the lowest sticker price otherwise.
function bestValueIndex(listings: Listing[]): number {
  const unit = listings.map(perOunce)
  if (unit.some((u) => u == null)) return 0
  return unit.indexOf(Math.min(...(unit as number[])))
}

export function WhereToBuy({ listings }: { listings: Listing[] }) {
  if (listings.length === 0) {
    return <p className="muted">No stores carry this product yet.</p>
  }
  const best = bestValueIndex(listings)
  return (
    <table className="stores">
      <thead className="visually-hidden">
        <tr>
          <th>Store</th>
          <th>Size</th>
          <th>Price</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        {listings.map((l, i) => {
          const unit = perOunce(l)
          return (
            <tr key={`${l.retailer}-${l.size}`}>
              <td className="stores__retailer">
                {l.retailer}
                {i === best && listings.length > 1 && <span className="flag">Best value</span>}
              </td>
              <td className="stores__size muted">{l.size}</td>
              <td className="stores__price">
                {formatPrice(l.price_usd)}
                {unit != null && <span className="muted"> {formatPrice(unit)}/oz</span>}
              </td>
              <td className="stores__link">
                <a href={l.url} target="_blank" rel="noopener noreferrer">
                  Visit store
                </a>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
