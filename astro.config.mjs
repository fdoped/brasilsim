import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://bolaverso.com',
  integrations: [sitemap()],
  build: { format: 'directory' },
});