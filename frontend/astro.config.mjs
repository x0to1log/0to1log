import { defineConfig } from 'astro/config';
import vercel from '@astrojs/vercel';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://0to1log.com',
  adapter: vercel(),

  prefetch: {
    defaultStrategy: 'hover',
  },

  integrations: [
    sitemap(),
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
