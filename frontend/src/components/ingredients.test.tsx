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

const NAMES = ['Water', 'Shea butter', 'Aloe vera juice', 'Glycerin', 'Coconut oil', 'Xanthan gum', 'Citric acid']
const formula = (n: number): FormulaLine[] =>
  NAMES.slice(0, n).map((name, i) => ({ ingredient: ingredient(`i${i}`, name, i === 0) }))

const names = (html: string) =>
  [...html.matchAll(/class="ingredient__name">([^<]*)</g)].map((m) => m[1])

describe('ingredient list', () => {
  it('shows the first five in label order, then a show more button', () => {
    const html = renderToStaticMarkup(<IngredientList formula={formula(7)} />)
    expect(names(html)).toEqual(NAMES.slice(0, 5))
    expect(html).toContain('Show more</button>')
  })

  it('shows every ingredient and no button when there are five or fewer', () => {
    const html = renderToStaticMarkup(<IngredientList formula={formula(5)} />)
    expect(names(html)).toEqual(NAMES.slice(0, 5))
    expect(html).not.toContain('Show more')
  })

  it('renders no amounts', () => {
    const html = renderToStaticMarkup(<IngredientList formula={formula(3)} />)
    expect(html).not.toContain('%')
    expect(html).not.toContain('ingredient__bar')
  })
})

describe('similar products', () => {
  it('lists shared ingredients in the order given, without amount columns', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <ProfileProvider>
          <SimilarProducts
            items={[
              {
                product,
                similarity: 0.5,
                shared: [
                  { ingredient_id: 'shea', name: 'Shea butter' },
                  { ingredient_id: 'glycerin', name: 'Glycerin' },
                ],
              },
            ]}
          />
        </ProfileProvider>
      </MemoryRouter>,
    )
    expect([...html.matchAll(/<th scope="row">([^<]*)</g)].map((m) => m[1])).toEqual(['Shea butter', 'Glycerin'])
    expect(html).toContain('In both')
    expect(html).not.toContain('This one')
  })
})
