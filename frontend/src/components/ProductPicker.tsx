import { api } from '../api'
import type { ProductSummary } from '../types'
import { SearchCombobox } from './SearchCombobox'

interface Props {
  excludeIds: string[]
  onPick: (product: ProductSummary) => void
}

/** Type-ahead for adding products you already like or use. */
export function ProductPicker({ excludeIds, onPick }: Props) {
  return (
    <SearchCombobox<ProductSummary>
      label="Add a product you like or use"
      placeholder="Add a product by name or brand"
      search={async (q) => {
        const found = await api.searchProducts(q, 12)
        return found.filter((p) => !excludeIds.includes(p.id)).slice(0, 6)
      }}
      getKey={(p) => p.id}
      renderOption={(p) => (
        <>
          <span>{p.name}</span>
          <span className="muted">{p.brand}</span>
        </>
      )}
      onPick={onPick}
    />
  )
}
