import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

interface Props<T> {
  label: string
  placeholder: string
  search: (query: string) => Promise<T[]>
  getKey: (item: T) => string
  renderOption: (item: T) => ReactNode
  onPick: (item: T) => void
  /** Characters required before searching. 0 = show suggestions on focus. */
  minChars?: number
  autoFocus?: boolean
  onEscape?: () => void
}

/** Type-ahead input with a keyboard-navigable suggestion list (ARIA combobox pattern). */
export function SearchCombobox<T>({
  label,
  placeholder,
  search,
  getKey,
  renderOption,
  onPick,
  minChars = 0,
  autoFocus,
  onEscape,
}: Props<T>) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState<T[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const listId = useId()

  // Callers pass inline functions; reading through a ref keeps a new function
  // identity on every parent render from refiring the search.
  const searchRef = useRef(search)
  useEffect(() => {
    searchRef.current = search
  })

  const searchable = query.trim().length >= minChars

  useEffect(() => {
    if (!open || !searchable) return
    let cancelled = false
    const timer = setTimeout(() => {
      searchRef.current(query).then(
        (found) => {
          if (cancelled) return
          setOptions(found)
          setActive(0)
        },
        () => !cancelled && setOptions([]),
      )
    }, 150)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, open, searchable])

  const pick = (item: T) => {
    onPick(item)
    setQuery('')
    setOpen(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((i) => Math.min(i + 1, options.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && open && options[active]) {
      e.preventDefault()
      pick(options[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
      onEscape?.()
    }
  }

  // Options from a longer query linger after deleting below minChars; hide them.
  const showList = open && searchable && options.length > 0

  return (
    <div className="picker">
      <input
        type="text"
        className="input"
        aria-label={label}
        placeholder={placeholder}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${listId}-${active}` : undefined}
        autoFocus={autoFocus}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {showList && (
        <ul className="picker__list" role="listbox" id={listId} aria-label={label}>
          {options.map((item, i) => (
            <li
              key={getKey(item)}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className="picker__option"
              // Keeps focus in the input so its onBlur doesn't close the list before onClick runs.
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(item)}
              onMouseEnter={() => setActive(i)}
            >
              {renderOption(item)}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
