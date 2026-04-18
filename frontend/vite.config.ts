import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import svgLoader from 'vite-svg-loader'

import { fileURLToPath, URL } from 'node:url'

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
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || env.VITE_API_URL || 'http://localhost:8001';

  return {
    plugins: [vue(), UnoCSS(), svgLoader()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return;

            if (id.includes('echarts')) return 'echarts';
            if (id.includes('@element-plus/icons-vue')) return 'element-plus-icons';
            if (id.includes('element-plus')) {
              return 'element-plus';
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
      },
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
          target: apiProxyTarget,
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
    },
  };
})
