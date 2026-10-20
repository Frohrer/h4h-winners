import type { CSSProperties, ReactElement } from 'react'
import type { ProductSummary } from '../types'

// Stand-in packaging drawn from the product's category and tint, used until
// scraped photos fill image_url. Cap = ink, body = product color, label = white.

type Container = 'bottle' | 'spray' | 'jar' | 'tin' | 'tube' | 'dropper' | 'can'

const CONTAINER_BY_CATEGORY: Record<string, Container> = {
  Shampoo: 'bottle',
  Conditioner: 'bottle',
  'Co-wash': 'bottle',
  'Leave-in conditioner': 'spray',
  'Treatment spray': 'spray',
  'Curl cream': 'jar',
  'Deep conditioner': 'jar',
  'Hair butter': 'jar',
  'Edge control': 'tin',
  Gel: 'tube',
  'Hair oil': 'dropper',
  'Scalp serum': 'dropper',
  Mousse: 'can',
}

const CAP = 'var(--ink)'
const LABEL = '#fff'

function shape(kind: Container, body: string): ReactElement {
  switch (kind) {
    case 'spray':
      return (
        <>
          <rect x="64" y="46" width="24" height="8" rx="2" fill={CAP} />
          <path d="M84 40h38v22H84z" fill={CAP} />
          <path d="M92 62l-6 22h8l6-22z" fill={CAP} />
          <rect x="90" y="62" width="22" height="14" fill={CAP} />
          <rect x="70" y="76" width="62" height="96" rx="12" fill={body} />
          <rect x="78" y="104" width="46" height="40" rx="3" fill={LABEL} opacity="0.85" />
        </>
      )
    case 'jar':
      return (
        <>
          <rect x="50" y="90" width="100" height="22" rx="5" fill={CAP} />
          <rect x="54" y="110" width="92" height="62" rx="10" fill={body} />
          <rect x="54" y="124" width="92" height="30" fill={LABEL} opacity="0.85" />
        </>
      )
    case 'tin':
      return (
        <>
          <rect x="44" y="124" width="112" height="18" rx="8" fill={CAP} />
          <rect x="48" y="140" width="104" height="32" rx="8" fill={body} />
        </>
      )
    case 'tube':
      return (
        <>
          <rect x="68" y="34" width="64" height="10" rx="2" fill={body} />
          <path d="M68 44h64l-12 104H80z" fill={body} />
          <rect x="84" y="148" width="32" height="24" rx="4" fill={CAP} />
          <rect x="82" y="72" width="36" height="44" rx="3" fill={LABEL} opacity="0.85" />
        </>
      )
    case 'dropper':
      return (
        <>
          <ellipse cx="100" cy="64" rx="10" ry="14" fill={CAP} />
          <rect x="86" y="74" width="28" height="18" rx="3" fill={CAP} />
          <rect x="74" y="92" width="52" height="80" rx="12" fill={body} />
          <rect x="80" y="112" width="40" height="34" rx="3" fill={LABEL} opacity="0.85" />
        </>
      )
    case 'can':
      return (
        <>
          <rect x="92" y="32" width="16" height="12" rx="2" fill={CAP} />
          <rect x="78" y="42" width="44" height="28" rx="10" fill={CAP} />
          <rect x="72" y="68" width="56" height="104" rx="10" fill={body} />
          <rect x="78" y="98" width="44" height="42" rx="3" fill={LABEL} opacity="0.85" />
        </>
      )
    default:
      return (
        <>
          <rect x="82" y="36" width="36" height="20" rx="4" fill={CAP} />
          <rect x="66" y="54" width="68" height="118" rx="14" fill={body} />
          <rect x="74" y="92" width="52" height="44" rx="3" fill={LABEL} opacity="0.85" />
        </>
      )
  }
}

export function ProductImage({ product, className }: { product: ProductSummary; className?: string }) {
  const style = { '--tint': product.color } as CSSProperties
  if (product.image_url) {
    return (
      <div className={`product-image ${className ?? ''}`} style={style}>
        <img src={product.image_url} alt="" />
      </div>
    )
  }
  const kind = CONTAINER_BY_CATEGORY[product.category] ?? 'bottle'
  return (
    <div className={`product-image ${className ?? ''}`} style={style}>
      <svg viewBox="0 0 200 200" role="img" aria-label={`${product.category} packaging`}>
        {shape(kind, product.color)}
      </svg>
    </div>
  )
}
