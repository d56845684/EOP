import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import svgLoader from 'vite-svg-loader'

import { fileURLToPath, URL } from 'node:url'

const elementPlusChunkMap: Record<string, string> = {
  alert: 'element-plus-misc',
  aside: 'element-plus-layout',
  autocomplete: 'element-plus-form',
  avatar: 'element-plus-data',
  badge: 'element-plus-misc',
  button: 'element-plus-misc',
  calendar: 'element-plus-misc',
  card: 'element-plus-data',
  checkbox: 'element-plus-form',
  col: 'element-plus-layout',
  'config-provider': 'element-plus-core',
  container: 'element-plus-layout',
  'date-picker': 'element-plus-form',
  descriptions: 'element-plus-data',
  dialog: 'element-plus-overlay',
  divider: 'element-plus-layout',
  drawer: 'element-plus-overlay',
  dropdown: 'element-plus-overlay',
  empty: 'element-plus-data',
  footer: 'element-plus-layout',
  form: 'element-plus-form',
  header: 'element-plus-layout',
  icon: 'element-plus-misc',
  image: 'element-plus-data',
  input: 'element-plus-form',
  'input-number': 'element-plus-form',
  loading: 'element-plus-overlay',
  main: 'element-plus-layout',
  menu: 'element-plus-layout',
  message: 'element-plus-overlay',
  'message-box': 'element-plus-overlay',
  notification: 'element-plus-overlay',
  option: 'element-plus-form',
  pagination: 'element-plus-data',
  popconfirm: 'element-plus-overlay',
  popper: 'element-plus-overlay',
  radio: 'element-plus-form',
  row: 'element-plus-layout',
  scrollbar: 'element-plus-layout',
  select: 'element-plus-form',
  skeleton: 'element-plus-data',
  switch: 'element-plus-form',
  'tab-pane': 'element-plus-overlay',
  table: 'element-plus-data',
  tabs: 'element-plus-overlay',
  tag: 'element-plus-data',
  'time-picker': 'element-plus-form',
  tooltip: 'element-plus-overlay',
  upload: 'element-plus-form',
};

const rewriteDevSetCookie = (setCookieHeader: string | string[] | undefined) => {
  if (!setCookieHeader) return undefined;

  const cookies = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
  return cookies.map((cookie) =>
    cookie
      .replace(/;\s*Domain=[^;]*/gi, '')
      .replace(/;\s*SameSite=None/gi, '; SameSite=Lax')
      .replace(/;\s*Secure/gi, '')
  );
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), UnoCSS(), svgLoader()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return;

          if (id.includes('echarts')) return 'echarts';
          if (id.includes('@element-plus/icons-vue')) return 'element-plus-icons';
          if (id.includes('element-plus')) {
            const componentMatch = id.match(/element-plus\/es\/components\/([^/]+)/);
            if (componentMatch) {
              return elementPlusChunkMap[componentMatch[1]] || 'element-plus-core';
            }
            if (
              id.includes('element-plus/es/directives') ||
              id.includes('element-plus/es/hooks') ||
              id.includes('element-plus/es/utils') ||
              id.includes('element-plus/es/tokens') ||
              id.includes('element-plus/es/constants') ||
              id.includes('element-plus/es/locale')
            ) {
              return 'element-plus-core';
            }
            return 'element-plus-core';
          }
          if (
            id.includes('/vue/') ||
            id.includes('vue-router') ||
            id.includes('pinia') ||
            id.includes('pinia-plugin-persistedstate') ||
            id.includes('vue-i18n') ||
            id.includes('@vueuse/core')
          ) {
            return 'vue-vendor';
          }
          if (id.includes('dayjs')) return 'dayjs';

          return 'vendor';
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: ``,
        quietDeps: true,
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        secure: false,
        target: 'http://13.159.135.69:8001',
        // target: 'https://preintelligent-claudette-oathfully.ngrok-free.dev/',
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyRes', (proxyRes) => {
            const rewrittenCookies = rewriteDevSetCookie(proxyRes.headers['set-cookie']);
            if (rewrittenCookies) {
              proxyRes.headers['set-cookie'] = rewrittenCookies;
            }
          });
        },
      }
    }
  }
})
