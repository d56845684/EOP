/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#ecf5ff',
          100: '#d9ecff',
          200: '#b3d8ff',
          300: '#8cc5ff',
          400: '#66b1ff',
          500: '#409eff',
          600: '#337ecc',
          700: '#265f99',
          800: '#1a3f66',
          900: '#0d2033',
        },
        ep: {
          success: '#67c23a',
          warning: '#e6a23c',
          danger: '#f56c6c',
          info: '#909399',
          bg: '#f5f7fa',
          border: '#dcdfe6',
          'text-primary': '#303133',
          'text-secondary': '#606266',
          'text-disabled': '#a8abb2',
        },
      },
    },
  },
  plugins: [],
}
