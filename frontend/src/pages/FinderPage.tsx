import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { EnvironmentNote } from '../components/EnvironmentNote'
import { HairTypePicker } from '../components/HairTypePicker'
import { LocationField } from '../components/LocationField'
import { ProductTile } from '../components/ProductTile'
import { TraitPicker } from '../components/TraitPicker'
import { formatList } from '../format'
import { useProfile } from '../profileContext'
import type { Location, Porosity, RecommendationResponse, Thickness } from '../types'
import { useAsync, type AsyncState } from '../useAsync'

const POROSITY: Porosity[] = ['low', 'medium', 'high']
const THICKNESS: Thickness[] = ['fine', 'medium', 'coarse']
const PAGE = 24

export function FinderPage() {
  const profile = useProfile()
  // The query lives in the URL so "Back" from a product page restores the results.
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const [draft, setDraft] = useState(q)
  // Re-sync the input when the URL changes underneath it (Back, Clear search).
  const [syncedQ, setSyncedQ] = useState(q)
  if (q !== syncedQ) {
    setSyncedQ(q)
    setDraft(q)
  }

  // Favorites and "I use this" still feed the ranking, but only take effect on
  // the next search. The recommender skips products you already have, so
  // re-ranking on every heart click would yank the hearted tile out from
  // under the cursor.
  const [rankKey, setRankKey] = useState(0)
  const rerank = () => setRankKey((k) => k + 1)

  const location = profile.activeLocation
  const locationKey = location ? `${location.latitude},${location.longitude}` : 'none'

  // "Show more" asks for a longer list of the same ranking; a new search starts over.
  const searchKey = [profile.hairTypes.join(','), profile.porosity, profile.thickness, q, locationKey, rankKey].join('|')
  const [shown, setShown] = useState(PAGE)
  const [shownFor, setShownFor] = useState(searchKey)
  if (searchKey !== shownFor) {
    setShownFor(searchKey)
    setShown(PAGE)
  }

  const recs = useAsync(
    () =>
      api.recommend({
        hair_types: profile.hairTypes,
        // undefined is dropped by JSON.stringify, so unset traits aren't sent.
        porosity: profile.porosity ?? undefined,
        thickness: profile.thickness ?? undefined,
        liked_product_ids: profile.favorites,
        current_product_ids: profile.using,
        query: q,
        location,
        limit: shown,
      }),
    [searchKey, shown],
    // Wait out IP detection so the first results already include climate,
    // instead of rendering once without it and reshuffling a second later.
    !profile.detecting,
  )

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const next = draft.trim()
    setParams(next ? { q: next } : {})
    rerank()
  }

  return (
    <div className="finder">
      <HairSection />

      <section className="finder__inputs">
        <div className="field">
          <h2 className="field__label">Where you live</h2>
          <p className="field__hint">
            We use this to check your local climate. Humidity and dew point change how products behave in your hair,
            especially gels and anything with glycerin.
          </p>
          <LocationField />
        </div>

        <form className="field" onSubmit={submit} role="search">
          <label className="field__label" htmlFor="query">
            What are you looking for?
          </label>
          <div className="search">
            <input
              id="query"
              className="input input--large"
              type="search"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Try “less shrinkage”, “lightweight moisture”, or “gel for wash-and-go”"
            />
            <button type="submit" className="button button--primary">
              Find products
            </button>
          </div>
        </form>
      </section>

      <Results
        recs={recs}
        q={q}
        location={location}
        onClear={() => setParams({})}
        onMore={() => setShown((n) => n + PAGE)}
      />
    </div>
  )
}

function HairSection() {
  const profile = useProfile()
  const hairTypes = useAsync(api.hairTypes, [])
  return (
    <section className="finder__hero" aria-labelledby="hair-type-heading">
      <h1 id="hair-type-heading" className="display">
        What's your hair type?
      </h1>
      {hairTypes.data && (
        <HairTypePicker hairTypes={hairTypes.data} selected={profile.hairTypes} onToggle={profile.toggleHairType} />
      )}
      <div className="finder__traits">
        <TraitPicker
          legend="Porosity"
          options={POROSITY}
          selected={profile.porosity}
          onToggle={(v) => profile.toggleTrait('porosity', v)}
        />
        <TraitPicker
          legend="Strands"
          options={THICKNESS}
          selected={profile.thickness}
          onToggle={(v) => profile.toggleTrait('thickness', v)}
        />
      </div>
      {hairTypes.error && <ApiDown />}
    </section>
  )
}

interface ResultsProps {
  recs: AsyncState<RecommendationResponse>
  q: string
  location: Location | null
  onClear: () => void
  onMore: () => void
}

function Results({ recs, q, location, onClear, onMore }: ResultsProps) {
  const { hairTypes } = useProfile()
  const results = recs.data?.results ?? []
  const title = [hairTypes.length ? `For ${formatList(hairTypes)} hair` : 'All products', q && `matching “${q}”`]
    .filter(Boolean)
    .join(' ')

  return (
    <section className="results" aria-labelledby="results-heading" aria-busy={recs.loading}>
      <div className="results__head">
        <h2 id="results-heading">{title}</h2>
        {recs.data && <p className="muted">{recs.data.total} products</p>}
      </div>

      {recs.data?.environment && location && <EnvironmentNote environment={recs.data.environment} location={location} />}

      {recs.error && <ApiDown />}

      {recs.data && results.length === 0 && (
        <div className="empty">
          <p>
            Nothing matches “{q}”
            {hairTypes.length > 0 && ` for ${formatList(hairTypes)} hair`}. Try fewer words, or clear the search.
          </p>
          <button type="button" className="button" onClick={onClear}>
            Clear search
          </button>
        </div>
      )}

      <div className="grid">
        {results.map((r) => (
          <ProductTile key={r.product.id} product={r.product} reasons={r.reasons} warnings={r.warnings} />
        ))}
      </div>

      {recs.data && results.length < recs.data.total && (
        <div className="results__more">
          <button type="button" className="button" onClick={onMore} disabled={recs.loading}>
            Show more
          </button>
        </div>
      )}
    </section>
  )
}

export function ApiDown() {
  return (
    <p className="notice">
      The product service isn't responding. Start it with <code>uv run fastapi dev app/main.py</code> in{' '}
      <code>backend/</code>, then reload.
    </p>
  )
}
