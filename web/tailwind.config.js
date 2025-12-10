/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Industrial control panel theme
        panel: {
          bg: '#1a1d23',
          surface: '#23272f',
          border: '#363b44',
          highlight: '#2d3139',
        },
        // LCD display colors
        lcd: {
          bg: '#0d1117',
          text: '#58a6ff',
          dim: '#238636',
          warn: '#d29922',
          error: '#f85149',
        },
        // Status colors
        status: {
          running: '#3fb950',
          idle: '#8b949e',
          error: '#f85149',
          warning: '#d29922',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'SF Mono', 'Consolas', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        },
      },
    },
  },
  plugins: [],
};


