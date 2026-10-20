import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { DataPage } from './pages/DataPage'
import { FinderPage } from './pages/FinderPage'
import { MyProductsPage } from './pages/MyProductsPage'
import { ProductPage } from './pages/ProductPage'
import { useProfile } from './profile'

export function App() {
  const profile = useProfile()
  const mine = new Set([...profile.favorites, ...profile.using]).size

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="masthead">
        <Link to="/" className="wordmark">
          Strand
        </Link>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Find products
          </NavLink>
          <NavLink to="/me">
            My products{mine > 0 && <span className="count">{mine}</span>}
          </NavLink>
          <NavLink to="/data">Our data</NavLink>
        </nav>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<FinderPage />} />
          <Route path="/products/:id" element={<ProductPage />} />
          <Route path="/me" element={<MyProductsPage />} />
          <Route path="/data" element={<DataPage />} />
          <Route
            path="*"
            element={
              <div className="empty">
                <h1>This page doesn't exist</h1>
                <Link to="/" className="button">
                  Find products
                </Link>
              </div>
            }
          />
        </Routes>
      </main>
    </>
  )
}
