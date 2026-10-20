// Each hair type is drawn as a single strand so the picker shows the texture
// instead of making people decode "3B" from memory. Shapes are generated, not
// hand-drawn, so they stay consistent with each other.

const W = 28
const H = 72
const PAD = 4

type Shape =
  | { kind: 'wave'; amp: number; cycles: number }
  | { kind: 'curl'; radius: number; cycles: number }
  | { kind: 'zigzag'; amp: number; segments: number }

const SHAPES: Record<string, Shape> = {
  '1A': { kind: 'wave', amp: 0, cycles: 1 },
  '1B': { kind: 'wave', amp: 1.5, cycles: 0.75 },
  '1C': { kind: 'wave', amp: 2.5, cycles: 1.25 },
  '2A': { kind: 'wave', amp: 4, cycles: 1.5 },
  '2B': { kind: 'wave', amp: 6, cycles: 2 },
  '2C': { kind: 'wave', amp: 8, cycles: 2.5 },
  // A curl is a point circling while it travels down (a trochoid). Once the
  // radius outruns the downward speed, the path loops back on itself.
  '3A': { kind: 'curl', radius: 7.5, cycles: 2.5 },
  '3B': { kind: 'curl', radius: 6.5, cycles: 3.5 },
  '3C': { kind: 'curl', radius: 5.5, cycles: 4.5 },
  '4A': { kind: 'curl', radius: 4.5, cycles: 6.5 },
  '4B': { kind: 'zigzag', amp: 6, segments: 11 },
  '4C': { kind: 'zigzag', amp: 4.5, segments: 18 },
}

function points(shape: Shape): [number, number][] {
  const cx = W / 2
  const len = H - PAD * 2
  const pts: [number, number][] = []

  if (shape.kind === 'zigzag') {
    for (let i = 0; i <= shape.segments; i++) {
      const x = i === 0 || i === shape.segments ? cx : cx + (i % 2 ? shape.amp : -shape.amp)
      pts.push([x, PAD + (len * i) / shape.segments])
    }
    return pts
  }

  const steps = 160
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * Math.PI * 2 * shape.cycles
    if (shape.kind === 'wave') {
      pts.push([cx + shape.amp * Math.sin(t), PAD + (len * i) / steps])
    } else {
      // Flattened vertically so loops read as coils seen from the side.
      const ry = shape.radius * 0.55
      const speed = (len - 2 * ry) / (Math.PI * 2 * shape.cycles)
      const x = cx + shape.radius * 0.9 * Math.sin(t)
      const y = PAD + speed * t + ry * (1 - Math.cos(t))
      pts.push([x, y])
    }
  }
  return pts
}

const pathCache = new Map<string, string>()

function pathFor(code: string): string {
  const cached = pathCache.get(code)
  if (cached) return cached
  const shape = SHAPES[code] ?? SHAPES['1A']
  const d = points(shape)
    .map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}`)
    .join('')
  pathCache.set(code, d)
  return d
}

export function StrandGlyph({ code, className }: { code: string; className?: string }) {
  return (
    <svg className={className} viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true">
      <path d={pathFor(code)} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
