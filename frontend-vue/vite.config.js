import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/student': 'http://localhost:8088',
      '/score': 'http://localhost:8088',
      '/Employment': 'http://localhost:8088',
      '/class': 'http://localhost:8088',
      '/teacher': 'http://localhost:8088',
      '/teachers': 'http://localhost:8088',
      '/statistics': 'http://localhost:8088',
      '/work': 'http://localhost:8088',
      '/email': 'http://localhost:8088',
      '/nl2sql': 'http://localhost:8088',
      '/rag': 'http://localhost:8088'
    }
  }
})
