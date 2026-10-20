import type { DewPointBand, Environment, Location } from '../types'
import { formatTemp } from '../format'

const HEADLINE: Record<DewPointBand, string> = {
  dry: 'Dry air',
  comfortable: 'Mild humidity',
  humid: 'Humid air',
}

/** Shows which conditions shaped the results, so the climate nudge isn't invisible. */
export function EnvironmentNote({ environment, location }: { environment: Environment; location: Location }) {
  const cc = location.country_code
  return (
    <aside className={`environment environment--${environment.dew_point_band}`}>
      <p className="environment__headline">
        {HEADLINE[environment.dew_point_band]} near {location.city ?? location.label} today
      </p>
      <p className="environment__readings">
        {formatTemp(environment.temperature_c, cc)} with {Math.round(environment.relative_humidity_pct)}% humidity
        and a dew point of {formatTemp(environment.dew_point_c, cc)}
      </p>
      <p>{environment.advice}</p>
    </aside>
  )
}
