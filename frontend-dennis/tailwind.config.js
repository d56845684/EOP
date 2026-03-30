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
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#4f6ef7',
          600: '#3b53d9',
          700: '#2f42b3',
          800: '#243389',
          900: '#1a2560',
        },
        ep: {
          success: '#22c55e',
          warning: '#f59e0b',
          danger: '#ef4444',
          info: '#64748b',
          bg: '#f8fafc',
          border: '#e2e8f0',
          'text-primary': '#0f172a',
          'text-secondary': '#334155',
          'text-disabled': '#94a3b8',
        },
      },
      borderRadius: {
        DEFAULT: '10px',
        sm: '6px',
        lg: '14px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)',
        modal: '0 20px 40px -4px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [],
}
