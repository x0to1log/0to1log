import { defineConfig } from 'astro/config';
import vercel from '@astrojs/vercel';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import tailwindcss from '@tailwindcss/vite';
import { fetchSitemapUrls } from './scripts/sitemap-urls.mjs';

const dynamicUrls = await fetchSitemapUrls();

export default defineConfig({
  site: 'https://0to1log.com',
  adapter: vercel(),

  prefetch: {
    defaultStrategy: 'hover',
  },

  integrations: [
    sitemap({
      filter: (page) =>
        !page.includes('/admin') &&
        !page.includes('/auth/') &&
        !page.includes('/preview/') &&
        !page.includes('/login') &&
        !page.includes('/settings') &&
        !page.includes('/library'),
      customPages: dynamicUrls,
    }),
    mdx(),
  ],

  vite: {
    plugins: [tailwindcss()],
  },

  markdown: {
    shikiConfig: {
      theme: 'css-variables',
    },
  },
});
