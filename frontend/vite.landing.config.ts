import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  cacheDir: '.cache-landing',
  publicDir: 'landing-public',
  build: { outDir: 'dist-landing', emptyOutDir: true, sourcemap: false,
    rollupOptions: { input: 'landing.html' } },
  server: { host: '127.0.0.1', port: 4174, strictPort: true },
  preview: { host: '127.0.0.1', port: 4174, strictPort: true },
});
