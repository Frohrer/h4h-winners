import { useProfile } from '../profile'

export function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        d="M12 20.5s-7.5-4.6-9.2-9.4C1.6 7.6 4 4.5 7.3 4.5c2 0 3.6 1.1 4.7 2.8 1.1-1.7 2.7-2.8 4.7-2.8 3.3 0 5.7 3.1 4.5 6.6-1.7 4.8-9.2 9.4-9.2 9.4z"
        fill={filled ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/** Compact heart for product tiles. */
export function FavoriteToggle({ productId, productName }: { productId: string; productName: string }) {
  const profile = useProfile()
  const on = profile.has('favorites', productId)
  return (
    <button
      type="button"
      className="favorite-toggle"
      aria-pressed={on}
      aria-label={on ? `Remove ${productName} from favorites` : `Save ${productName} to favorites`}
      onClick={() => profile.toggle('favorites', productId)}
    >
      <HeartIcon filled={on} />
    </button>
  )
}

/** Full-size actions for the product page. */
export function SaveButtons({ productId }: { productId: string }) {
  const profile = useProfile()
  const favorite = profile.has('favorites', productId)
  const using = profile.has('using', productId)
  return (
    <div className="save-buttons">
      <button
        type="button"
        className={`button ${favorite ? 'button--on' : ''}`}
        aria-pressed={favorite}
        onClick={() => profile.toggle('favorites', productId)}
      >
        <HeartIcon filled={favorite} />
        {favorite ? 'Saved to favorites' : 'Save to favorites'}
      </button>
      <button
        type="button"
        className={`button ${using ? 'button--on' : ''}`}
        aria-pressed={using}
        onClick={() => profile.toggle('using', productId)}
      >
        {using ? 'In your routine' : 'I use this'}
      </button>
    </div>
  )
}
