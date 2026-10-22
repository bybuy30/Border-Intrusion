/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // ── Forest dark palette ────────────────────────────────────────────
        forest: {
          950: '#0b1209',
          900: '#111c0e',
          800: '#192815',
          700: '#22391d',
          600: '#2d4d27',
          500: '#3a6432',
          400: '#4e843e',
          300: '#68a356',
          200: '#90c27a',
          100: '#c0ddb0',
          50:  '#e8f5e1',
        },
        surface: {
          900: '#141a12',
          800: '#1c241a',
          700: '#232e20',
          600: '#2b3827',
          500: '#36452f',
        },
        amber: {
          600: '#d97706',
          500: '#f59e0b',
          400: '#fbbf24',
          300: '#fcd34d',
        },
        red: {
          700: '#b91c1c',
          600: '#dc2626',
          500: '#ef4444',
          400: '#f87171',
        },
        slate: {
          400: '#94a3b8',
          300: '#cbd5e1',
          200: '#e2e8f0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 3px 0 rgba(0,0,0,0.4), 0 1px 2px -1px rgba(0,0,0,0.3)',
        card:  '0 4px 6px -1px rgba(0,0,0,0.5), 0 2px 4px -2px rgba(0,0,0,0.3)',
      },
      borderRadius: {
        panel: '0.625rem',
      },
    },
  },
  plugins: [],
}
