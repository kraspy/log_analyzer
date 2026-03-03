import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy /api requests to the backend during local development.
    // In production (Docker), Nginx handles this proxying instead.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split vendor chunks to improve caching:
        // - antd: large UI library, changes rarely
        // - react-vendor: React core, almost never changes
        // - chart-vendor: data visualization libs
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'query-vendor': ['@tanstack/react-query'],
        },
      },
    },
  },
})
