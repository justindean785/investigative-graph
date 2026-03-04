/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
        heading: ['Rajdhani', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        border: 'rgba(255, 255, 255, 0.08)',
        input: 'rgba(0, 0, 0, 0.5)',
        ring: 'rgba(6, 182, 212, 0.5)',
        background: '#050505',
        foreground: '#f8fafc',
        primary: {
          DEFAULT: '#06b6d4',
          foreground: '#ffffff',
        },
        secondary: {
          DEFAULT: '#f59e0b',
          foreground: '#000000',
        },
        destructive: {
          DEFAULT: '#ef4444',
          foreground: '#ffffff',
        },
        muted: {
          DEFAULT: 'rgba(20, 20, 25, 0.4)',
          foreground: '#94a3b8',
        },
        accent: {
          DEFAULT: '#06b6d4',
          foreground: '#ffffff',
        },
        popover: {
          DEFAULT: 'rgba(10, 10, 12, 0.9)',
          foreground: '#f8fafc',
        },
        card: {
          DEFAULT: 'rgba(20, 20, 25, 0.4)',
          foreground: '#f8fafc',
        },
      },
      borderRadius: {
        lg: '0.25rem',
        md: '0.25rem',
        sm: '0.125rem',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow': '0 0 15px rgba(6, 182, 212, 0.3)',
        'glow-lg': '0 0 25px rgba(6, 182, 212, 0.4)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
