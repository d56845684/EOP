import { defineConfig, presetUno, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(), // 提供與 Tailwind 完全兼容的語法
    presetIcons({
      scale: 1, // 預設圖示大小
      warn: true, // 找不到圖示時在終端機警告
      autoInstall: true, // 開啟自動安裝
    }),
  ],
  content: {
    pipeline: {
      include: [
        /\.(vue|svelte|[jt]sx|mdx?|astro|elm|php|phtml|html)($|\?)/,
        'src/router/**/*.{js,ts}'
      ]
    }
  },
  theme: {
    colors: {
      st: {
        primary: '#0f52ba',
        secondary: '#0a3d91',
        background: '#faf8ff',
        surface: '#ffffff',
        success: '#48a111',
        warning: '#ff9b2f',
        error: '#ba1a1a',
        danger: '#fb4141',
        'surface-lowest': '#ffffff',
        'surface-low': '#f3f3fc',
        'surface-container': '#ededf6',
        'surface-high': '#e7e7f1',
        'surface-highest': '#e1e2eb',
        'surface-dim': '#d9d9e2',
        'on-surface': '#191b22',
        'on-surface-variant': '#434653',
        outline: '#737784',
        'outline-variant': '#c3c6d5',
      }
    },
    borderRadius: {
      'st-sm': '2px',
      'st-default': '4px',
      'st-md': '6px',
      'st-lg': '8px',
      'st-xl': '12px',
      'st-full': '9999px',
    },
    boxShadow: {
      'st-l1': '0 2px 4px rgba(0, 0, 0, 0.04)',
      'st-l2': '0 4px 8px rgba(0, 0, 0, 0.08)',
      'st-l3': '0 10px 20px rgba(0, 0, 0, 0.12)',
    }
  }
})
