import { createContext, useContext } from 'react'
import type { Location, Porosity, Thickness } from './types'

/**
 * 'set' = the default city or one the person chose.
 * 'off' = the person removed it; respect that until they choose a city again.
 */
export type LocationPref = { mode: 'set'; value: Location } | { mode: 'off' }

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
  /** The location to send with searches, or null if turned off. */
  activeLocation: Location | null
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
