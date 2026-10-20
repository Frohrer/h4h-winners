// Mirrors backend/app/models.py. Update both together.

export type HairFamily = 'Straight' | 'Wavy' | 'Curly' | 'Coily'

export interface HairType {
  code: string
  family: HairFamily
  description: string
}

export interface Ingredient {
  id: string
  name: string
  inci: string
  function: string
  what_it_does: string
  why_its_added: string
  is_base: boolean
}

export interface Listing {
  retailer: string
  price_usd: number
  size: string
  url: string
}

export interface ProductSummary {
  id: string
  name: string
  brand: string
  category: string
  hair_types: string[]
  tags: string[]
  color: string
  image_url: string | null
  price_from: number | null
}

export interface FormulaLine {
  ingredient: Ingredient
  concentration_pct: number | null
}

export interface ProductDetail extends ProductSummary {
  description: string
  listings: Listing[]
  formula: FormulaLine[]
}

export interface SharedIngredient {
  ingredient_id: string
  name: string
  this_pct: number | null
  other_pct: number | null
}

export interface SimilarProduct {
  product: ProductSummary
  similarity: number
  shared: SharedIngredient[]
}

export interface Recommendation {
  product: ProductSummary
  score: number
  reasons: string[]
}

export interface Location {
  label: string
  city: string | null
  region: string | null
  country_code: string | null
  latitude: number
  longitude: number
  source: 'ip' | 'manual'
}

export type DewPointBand = 'dry' | 'comfortable' | 'humid'

export interface Environment {
  temperature_c: number
  relative_humidity_pct: number
  dew_point_c: number
  uv_index: number | null
  dew_point_band: DewPointBand
  advice: string
}

export interface RecommendationRequest {
  hair_types: string[]
  liked_product_ids: string[]
  current_product_ids: string[]
  query: string
  location: Location | null
  limit?: number
}

export interface RecommendationResponse {
  results: Recommendation[]
  environment: Environment | null
}
