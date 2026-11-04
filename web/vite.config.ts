import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: `npm run dev` proxies API calls to the FastAPI server on :8000.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/scan': 'http://127.0.0.1:8000' } },
})
