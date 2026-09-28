import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    // `npm run dev` outside Docker: forward API calls to a backend on the
    // host, so the app talks to its own origin here exactly as it does
    // behind nginx in production.
    proxy: {
      '/api': { target: process.env.VITE_DEV_API || 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
    restoreMocks: true,
  },
});
