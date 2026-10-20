import { useState } from 'react'
import { api } from '../api'
import { useProfile } from '../profile'
import type { Location } from '../types'
import { SearchCombobox } from './SearchCombobox'

/**
 * Location is optional and always visible, so people can see what's being
 * used and change or remove it in one click. The "why we ask" copy lives with
 * the field label in FinderPage.
 */
export function LocationField() {
  const profile = useProfile()
  const [editing, setEditing] = useState(false)
  const pref = profile.location

  if (editing) {
    return (
      <div className="location location--editing">
        <SearchCombobox<Location>
          label="Search for a city"
          placeholder="Search for a city"
          minChars={2}
          autoFocus
          search={api.searchLocations}
          getKey={(l) => `${l.latitude},${l.longitude}`}
          renderOption={(l) => (
            <>
              <span>{l.label}</span>
              <span className="muted">{l.country_code}</span>
            </>
          )}
          onPick={(value) => {
            profile.setLocation({ mode: 'set', value })
            setEditing(false)
          }}
          onEscape={() => setEditing(false)}
        />
        <button type="button" className="link-button" onClick={() => setEditing(false)}>
          Cancel
        </button>
      </div>
    )
  }

  if (pref.mode === 'set') {
    return (
      <div className="location">
        <PinIcon />
        <span>
          Near <strong>{pref.value.label}</strong>
          <span className="muted">
            {pref.value.source === 'ip' ? ', based on your internet connection' : ''}
          </span>
        </span>
        <button type="button" className="link-button" onClick={() => setEditing(true)}>
          Change
        </button>
        <button type="button" className="link-button" onClick={() => profile.setLocation({ mode: 'off' })}>
          Remove
        </button>
      </div>
    )
  }

  if (profile.detecting) {
    return (
      <div className="location muted">
        <PinIcon />
        Finding your area
      </div>
    )
  }

  return (
    <div className="location">
      <PinIcon />
      <span className="muted">
        {pref.mode === 'off'
          ? 'Location is off, so results don’t account for your climate.'
          : 'We couldn’t detect where you are.'}
      </span>
      <button type="button" className="link-button" onClick={() => setEditing(true)}>
        Choose a city
      </button>
      {pref.mode === 'off' && (
        <button type="button" className="link-button" onClick={() => profile.setLocation({ mode: 'detect' })}>
          Detect my location
        </button>
      )}
    </div>
  )
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" className="location__pin">
      <path
        d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="10" r="2.3" fill="currentColor" />
    </svg>
  )
}
