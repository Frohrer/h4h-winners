import { useState } from 'react'
import type { FormulaLine } from '../types'

const SHOWN_INGREDIENTS = 5

export function IngredientList({ formula }: { formula: FormulaLine[] }) {
  const [asLabel, setAsLabel] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? formula : formula.slice(0, SHOWN_INGREDIENTS)

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
        <>
          <ul className="ingredients__list">
            {shown.map(({ ingredient }) => (
              <li key={ingredient.id}>
                <details className="ingredient">
                  <summary>
                    <span className="ingredient__name">{ingredient.name}</span>
                    <span className="ingredient__function">{ingredient.function}</span>
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
            ))}
          </ul>
          {shown.length < formula.length && (
            <div className="ingredients__more">
              <button type="button" className="button" onClick={() => setShowAll(true)}>
                Show more
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
