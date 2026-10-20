import type { HairFamily, HairType } from '../types'
import { StrandGlyph } from './StrandGlyph'

const FAMILIES: HairFamily[] = ['Straight', 'Wavy', 'Curly', 'Coily']

interface Props {
  hairTypes: HairType[]
  selected: string[]
  onToggle: (code: string) => void
}

// Multi-select on purpose: many people have more than one texture
// (looser at the crown, tighter at the nape), and recommendations should
// cover all of them.
export function HairTypePicker({ hairTypes, selected, onToggle: toggle }: Props) {
  const describe = hairTypes.filter((h) => selected.includes(h.code))

  return (
    <div className="hair-picker">
      <div className="hair-picker__families">
        {FAMILIES.map((family) => (
          <fieldset key={family} className="hair-family">
            <legend>{family}</legend>
            <div className="hair-family__types">
              {hairTypes
                .filter((h) => h.family === family)
                .map((h) => {
                  const on = selected.includes(h.code)
                  return (
                    <button
                      key={h.code}
                      type="button"
                      className="hair-type"
                      aria-pressed={on}
                      title={h.description}
                      onClick={() => toggle(h.code)}
                    >
                      <StrandGlyph code={h.code} className="hair-type__strand" />
                      <span className="hair-type__code">{h.code}</span>
                    </button>
                  )
                })}
            </div>
          </fieldset>
        ))}
      </div>
      <div className="hair-picker__detail" aria-live="polite">
        {describe.length === 0 ? (
          <p className="muted">Pick the strand that looks most like yours. Choose more than one if your hair varies.</p>
        ) : (
          <dl>
            {describe.map((h) => (
              <div key={h.code}>
                <dt>{h.code}</dt>
                <dd>{h.description}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  )
}
