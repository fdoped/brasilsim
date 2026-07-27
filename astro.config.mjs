import { defineConfig } from 'astro/config';

// IMPORTANTE: quando comprar seu domínio, troque a URL abaixo e descomente o sitemap.
// Como comprar: registro.br (.com.br) ou namecheap.com (.com)
export default defineConfig({
  site: 'https://brasilsim.pages.dev',   // provisório do Cloudflare Pages
  build: { format: 'directory' },
  // Depois de comprar domínio, instale @astrojs/sitemap e adicione:
  // integrations: [sitemap()],
});
