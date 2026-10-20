import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { EnvironmentNote } from '../components/EnvironmentNote'
import { HairTypePicker } from '../components/HairTypePicker'
import { LocationField } from '../components/LocationField'
import { ProductTile } from '../components/ProductTile'
import { formatList } from '../format'
import { useProfile } from '../profile'
import { useAsync } from '../useAsync'

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

  const hairTypes = useAsync(api.hairTypes, [])

  // Favorites and "I use this" still feed the ranking, but only take effect on
  // the next search. The recommender skips products you already have, so
  // re-ranking on every heart click would yank the hearted tile out from
  // under the cursor.
  const [rankKey, setRankKey] = useState(0)
  const rerank = () => setRankKey((k) => k + 1)

  const location = profile.activeLocation
  const locationKey = location ? `${location.latitude},${location.longitude}` : 'none'
  const recs = useAsync(
    () =>
      api.recommend({
        hair_types: profile.hairTypes,
        liked_product_ids: profile.favorites,
        current_product_ids: profile.using,
        query: q,
        location,
      }),
    [profile.hairTypes.join(','), q, locationKey, rankKey],
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

  const title = [
    profile.hairTypes.length ? `For ${formatList(profile.hairTypes)} hair` : 'All products',
    q && `matching “${q}”`,
  ]
    .filter(Boolean)
    .join(' ')

  const results = recs.data?.results ?? []

  return (
    <div className="finder">
      <section className="finder__hero" aria-labelledby="hair-type-heading">
        <h1 id="hair-type-heading" className="display">
          What's your hair type?
        </h1>
        {hairTypes.data && (
          <HairTypePicker
            hairTypes={hairTypes.data}
            selected={profile.hairTypes}
            onToggle={profile.toggleHairType}
          />
        )}
        {hairTypes.error && <ApiDown />}
      </section>

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

      <section className="results" aria-labelledby="results-heading" aria-busy={recs.loading}>
        <div className="results__head">
          <h2 id="results-heading">{title}</h2>
          {recs.data && <p className="muted">{results.length} products</p>}
        </div>

        {recs.data?.environment && location && (
          <EnvironmentNote environment={recs.data.environment} location={location} />
        )}

        {recs.error && <ApiDown />}

        {recs.data && results.length === 0 && (
          <div className="empty">
            <p>
              Nothing matches “{q}”
              {profile.hairTypes.length > 0 && ` for ${formatList(profile.hairTypes)} hair`}. Try fewer words, or
              clear the search.
            </p>
            <button type="button" className="button" onClick={() => setParams({})}>
              Clear search
            </button>
          </div>
        )}

        <div className="grid">
          {results.map((r) => (
            <ProductTile key={r.product.id} product={r.product} reasons={r.reasons} />
          ))}
        </div>
      </section>
    </div>
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
