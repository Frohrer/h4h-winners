interface Props<T extends string> {
  legend: string
  options: readonly T[]
  selected: T | null
  /** Called with the clicked option; the profile clears it if it was already selected. */
  onToggle: (value: T) => void
}

const label = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)

// Single choice that can be undone, so plain toggle buttons rather than a
// radiogroup: radios can't return to "nothing picked".
export function TraitPicker<T extends string>({ legend, options, selected, onToggle }: Props<T>) {
  return (
    <fieldset className="trait">
      <legend>{legend}</legend>
      <div className="trait__options">
        {options.map((value) => (
          <button
            key={value}
            type="button"
            className="trait__option"
            aria-pressed={selected === value}
            onClick={() => onToggle(value)}
          >
            {label(value)}
          </button>
        ))}
      </div>
    </fieldset>
  )
}
