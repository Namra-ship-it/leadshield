import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_URL || env.BACKEND_URL || env.VITE_PROXY_TARGET || env.PROXY_TARGET || process.env.VITE_PROXY_TARGET || process.env.PROXY_TARGET || process.env.VITE_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [
      react(),
      tailwindcss()
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true
        },
        '/health': {
          target: backendTarget,
          changeOrigin: true
        }
      }
    }
  }
})
