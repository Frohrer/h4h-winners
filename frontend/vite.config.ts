import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin /api in dev means no CORS setup on the FastAPI side.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
