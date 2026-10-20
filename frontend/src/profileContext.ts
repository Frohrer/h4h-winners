import { createContext, useContext } from 'react'
import type { Location, Porosity, Thickness } from './types'

/**
 * 'detect' = not decided yet; look it up from the connection once.
 * 'set'    = detected or chosen; never overwritten by detection again.
 * 'off'    = the person removed it; respect that until they turn it back on.
 */
export type LocationPref = { mode: 'detect' } | { mode: 'set'; value: Location } | { mode: 'off' }

export interface Profile {
  hairTypes: string[]
  porosity: Porosity | null
  thickness: Thickness | null
  favorites: string[]
  using: string[]
  location: LocationPref
}

export type ListKey = 'favorites' | 'using'
export type TraitKey = 'porosity' | 'thickness'

export interface ProfileApi extends Profile {
  /** The location to send with searches, or null if unknown or turned off. */
  activeLocation: Location | null
  detecting: boolean
  toggleHairType: (code: string) => void
  /** Picking the current value again clears it; both are optional. */
  toggleTrait: <K extends TraitKey>(key: K, value: NonNullable<Profile[K]>) => void
  setLocation: (pref: LocationPref) => void
  toggle: (list: ListKey, productId: string) => void
  has: (list: ListKey, productId: string) => boolean
  remove: (productId: string) => void
}

export const ProfileContext = createContext<ProfileApi | null>(null)

export function useProfile(): ProfileApi {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used inside <ProfileProvider>')
  return ctx
}
