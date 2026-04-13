import path from 'node:path'
import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const workspaceRoot = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  root: workspaceRoot,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.join(workspaceRoot, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/nexus-api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/nexus-api/, ''),
      },
      '/nexus-ingest': {
        target: 'http://127.0.0.1:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/nexus-ingest/, ''),
      },
    },
  },
})
