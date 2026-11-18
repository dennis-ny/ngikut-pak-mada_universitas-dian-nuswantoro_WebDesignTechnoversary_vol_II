// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  site: 'https://ashen3d.web.id',
  server: {
    host: true,
    port: 4321
  }
});
