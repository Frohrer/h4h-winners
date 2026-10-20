const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export const formatPrice = (n: number) => usd.format(n)

export function formatPct(n: number | null): string {
  if (n == null) return 'Unknown'
  if (n < 1) return `${n.toFixed(1)}%`
  return `${Number.isInteger(n) ? n : n.toFixed(1)}%`
}

// Places where Fahrenheit is the everyday unit; Celsius everywhere else.
const FAHRENHEIT = new Set(['US', 'PR', 'GU', 'VI', 'AS', 'MP', 'BS', 'KY', 'LR', 'PW', 'FM', 'MH'])

export function formatTemp(celsius: number, countryCode: string | null): string {
  const fahrenheit = FAHRENHEIT.has(countryCode ?? '')
  return fahrenheit ? `${Math.round((celsius * 9) / 5 + 32)}°F` : `${Math.round(celsius)}°C`
}

const listFormat = new Intl.ListFormat('en', { style: 'long', type: 'conjunction' })

export const formatList = (items: string[]) => listFormat.format(items)
