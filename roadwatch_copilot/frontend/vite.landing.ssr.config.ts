import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  cacheDir: '.cache-landing',
  publicDir: false,
  build: {
    ssr: 'src/landing-prerender.tsx',
    outDir: '.landing-ssr',
    emptyOutDir: true,
    copyPublicDir: false,
  },
});
