import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: '../extension',
    emptyOutDir: false,
    rollupOptions: {
      input: {
        sidepanel: 'sidepanel.html',
        studio: 'studio.html',
      },
    },
  },
})
