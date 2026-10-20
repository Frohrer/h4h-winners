import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ProfileContext, type ListKey, type LocationPref, type Profile, type ProfileApi, type TraitKey } from './profileContext'

// The profile lives in localStorage until there are accounts. Every
// recommendation request sends it in full, so the recommender never depends
// on server-side session state and moving this to a user table later won't
// change the API contract.

const STORAGE_KEY = 'strand.profile.v1'
const DEFAULT_LOCATION: LocationPref = {
  mode: 'set',
  value: {
    label: 'Philadelphia, Pennsylvania',
    city: 'Philadelphia',
    region: 'Pennsylvania',
    country_code: 'US',
    latitude: 39.9526,
    longitude: -75.1652,
    source: 'manual',
  },
}
const EMPTY: Profile = {
  hairTypes: [],
  porosity: null,
  thickness: null,
  favorites: [],
  using: [],
  location: DEFAULT_LOCATION,
}

function load(): Profile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    const stored = { ...EMPTY, ...JSON.parse(raw) }
    // Profiles saved while location came from IP lookup may still say
    // 'detect', meaning nothing was chosen yet: give them the default too.
    return stored.location.mode === 'detect' ? { ...stored, location: DEFAULT_LOCATION } : stored
  } catch {
    return EMPTY
  }
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile>(load)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  }, [profile])

  // Functional update: computing from a rendered `hairTypes` value would drop
  // all but the last of several toggles made before React re-renders.
  const toggleHairType = useCallback(
    (code: string) =>
      setProfile((p) => ({
        ...p,
        hairTypes: p.hairTypes.includes(code) ? p.hairTypes.filter((c) => c !== code) : [...p.hairTypes, code],
      })),
    [],
  )
  const toggleTrait = useCallback(
    <K extends TraitKey>(key: K, value: NonNullable<Profile[K]>) =>
      setProfile((p) => ({ ...p, [key]: p[key] === value ? null : value })),
    [],
  )
  const setLocation = useCallback((location: LocationPref) => setProfile((p) => ({ ...p, location })), [])

  const toggle = useCallback(
    (list: ListKey, id: string) =>
      setProfile((p) => ({
        ...p,
        [list]: p[list].includes(id) ? p[list].filter((x) => x !== id) : [id, ...p[list]],
      })),
    [],
  )

  const remove = useCallback(
    (id: string) =>
      setProfile((p) => ({
        ...p,
        favorites: p.favorites.filter((x) => x !== id),
        using: p.using.filter((x) => x !== id),
      })),
    [],
  )

  const value = useMemo<ProfileApi>(
    () => ({
      ...profile,
      activeLocation: profile.location.mode === 'set' ? profile.location.value : null,
      toggleHairType,
      toggleTrait,
      setLocation,
      toggle,
      remove,
      has: (list, id) => profile[list].includes(id),
    }),
    [profile, toggleHairType, toggleTrait, setLocation, toggle, remove],
  )

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
}
