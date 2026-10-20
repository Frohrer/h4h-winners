import { useState } from 'react'
import type { FormulaLine } from '../types'
import { formatPct } from '../format'

export function IngredientList({ formula }: { formula: FormulaLine[] }) {
  const [asLabel, setAsLabel] = useState(false)

  // Bars scale to the largest non-base ingredient. Scaling to water (often
  // 60-80%) would shrink every active ingredient to a sliver.
  const actives = formula.filter((l) => !l.ingredient.is_base)
  const scale = Math.max(...actives.map((l) => l.concentration_pct ?? 0), 1)

  return (
    <div className="ingredients">
      <div className="section-tools">
        <button type="button" className="link-button" onClick={() => setAsLabel((v) => !v)}>
          {asLabel ? 'Show ingredient details' : 'Show as printed on the label'}
        </button>
      </div>

      {asLabel ? (
        <p className="ingredients__label">{formula.map((l) => l.ingredient.inci).join(', ')}</p>
      ) : (
        <ul className="ingredients__list">
          {formula.map(({ ingredient, concentration_pct }) => {
            const width = ingredient.is_base ? 100 : ((concentration_pct ?? 0) / scale) * 100
            return (
              <li key={ingredient.id}>
                <details className="ingredient">
                  <summary>
                    <span className="ingredient__name">{ingredient.name}</span>
                    <span className="ingredient__function">{ingredient.function}</span>
                    <span className="ingredient__bar" aria-hidden="true">
                      <span
                        className={ingredient.is_base ? 'is-base' : undefined}
                        style={{ width: `${Math.min(width, 100)}%` }}
                      />
                    </span>
                    <span className="ingredient__pct">{formatPct(concentration_pct)}</span>
                  </summary>
                  <div className="ingredient__body">
                    <p>{ingredient.what_it_does}</p>
                    <p>
                      <strong>Why it's added: </strong>
                      {ingredient.why_its_added}
                    </p>
                    <p className="muted">On the label as {ingredient.inci}</p>
                  </div>
                </details>
              </li>
            )
          })}
        </ul>
      )}
      <p className="footnote">
        Brands rarely publish exact amounts. Percentages are estimates based on each ingredient's place on the label.
      </p>
    </div>
  )
}
