import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ProfileProvider } from '../profile'
import type { FormulaLine, Ingredient, ProductSummary } from '../types'
import { IngredientList } from './IngredientList'
import { SimilarProducts } from './SimilarProducts'

const ingredient = (id: string, name: string, is_base = false): Ingredient => ({
  id,
  name,
  inci: name,
  function: 'Humectant',
  what_it_does: '',
  why_its_added: '',
  is_base,
})

const product: ProductSummary = {
  id: 'p2',
  name: 'Other product',
  brand: 'Brand',
  category: 'Shampoo',
  hair_types: [],
  tags: [],
  color: '#000',
  image_url: null,
  price_from: null,
}

const renderSimilar = (this_pct: number | null, other_pct: number | null) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <ProfileProvider>
        <SimilarProducts
          items={[{ product, similarity: 0.5, shared: [{ ingredient_id: 'glycerin', name: 'Glycerin', this_pct, other_pct }] }]}
        />
      </ProfileProvider>
    </MemoryRouter>,
  )

describe('ingredient amounts', () => {
  // Scraped catalogs have no amount for any line.
  const scraped: FormulaLine[] = [
    { ingredient: ingredient('water', 'Water', true), concentration_pct: null },
    { ingredient: ingredient('glycerin', 'Glycerin'), concentration_pct: null },
  ]

  it('hides bars and amounts when none are known', () => {
    const html = renderToStaticMarkup(<IngredientList formula={scraped} />)
    expect(html).toContain('Glycerin')
    expect(html).not.toContain('Unknown')
    expect(html).not.toContain('ingredient__bar')
    expect(html).not.toContain('ingredient__pct')
    expect(html).not.toContain('Percentages are estimates')
  })

  it('shows amounts that are known and skips the rest', () => {
    const html = renderToStaticMarkup(
      <IngredientList formula={[{ ingredient: ingredient('shea', 'Shea butter'), concentration_pct: 12 }, ...scraped]} />,
    )
    expect(html.match(/class="ingredient__pct">([^<]*)</g)).toEqual(['class="ingredient__pct">12%<'])
    expect(html).toContain('Percentages are estimates')
  })

  it('drops the amount columns from similar products when none are known', () => {
    const html = renderSimilar(null, null)
    expect(html).toContain('Glycerin')
    expect(html).not.toContain('Unknown')
    expect(html).not.toContain('This one')
  })

  it('keeps the amount columns from similar products when known', () => {
    const html = renderSimilar(5, null)
    expect(html).toContain('This one')
    expect(html).toContain('<td>5%</td><td></td>')
  })
})
