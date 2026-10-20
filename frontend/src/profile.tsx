import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from './api'
import { ProfileContext, type ListKey, type LocationPref, type Profile, type ProfileApi, type TraitKey } from './profileContext'

// The profile lives in localStorage until there are accounts. Every
// recommendation request sends it in full, so the recommender never depends
// on server-side session state and moving this to a user table later won't
// change the API contract.

const STORAGE_KEY = 'strand.profile.v1'
const EMPTY: Profile = {
  hairTypes: [],
  porosity: null,
  thickness: null,
  favorites: [],
  using: [],
  location: { mode: 'detect' },
}

function load(): Profile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY, ...JSON.parse(raw) } : EMPTY
  } catch {
    return EMPTY
  }
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile>(load)
  const [detectFailed, setDetectFailed] = useState(false)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  }, [profile])

  // Runs once per page load at most. A failed lookup stays in 'detect' so the
  // next visit tries again, rather than silently turning location off.
  const needsDetect = profile.location.mode === 'detect'
  useEffect(() => {
    if (!needsDetect) return
    let cancelled = false
    api
      .detectLocation()
      .then((value) => {
        if (cancelled) return
        if (!value) return setDetectFailed(true)
        // Only fill in if the person hasn't chosen something in the meantime.
        setProfile((p) => (p.location.mode === 'detect' ? { ...p, location: { mode: 'set', value } } : p))
      })
      .catch(() => !cancelled && setDetectFailed(true))
    return () => {
      cancelled = true
    }
  }, [needsDetect])

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
  const setLocation = useCallback((location: LocationPref) => {
    setDetectFailed(false)
    setProfile((p) => ({ ...p, location }))
  }, [])

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
      detecting: profile.location.mode === 'detect' && !detectFailed,
      toggleHairType,
      toggleTrait,
      setLocation,
      toggle,
      remove,
      has: (list, id) => profile[list].includes(id),
    }),
    [profile, detectFailed, toggleHairType, toggleTrait, setLocation, toggle, remove],
  )

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
}
