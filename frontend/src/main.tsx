import '@fontsource/familjen-grotesk/400.css'
import '@fontsource/familjen-grotesk/500.css'
import '@fontsource/familjen-grotesk/600.css'
import '@fontsource/familjen-grotesk/700.css'
import './styles.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { ProfileProvider } from './profile'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ProfileProvider>
        <App />
      </ProfileProvider>
    </BrowserRouter>
  </StrictMode>,
)
