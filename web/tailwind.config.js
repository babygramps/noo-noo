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
        // Industrial control panel theme - refined slate palette
        panel: {
          bg: '#0f1218',
          surface: '#1a1f2a',
          border: '#2a3140',
          highlight: '#252d3d',
        },
        // LCD display colors - high contrast scientific look
        lcd: {
          bg: '#080c12',
          text: '#4fd1c5',
          dim: '#2dd4bf',
          warn: '#fbbf24',
          error: '#f87171',
          muted: '#64748b',
        },
        // Status colors - vibrant and clear
        status: {
          running: '#10b981',
          idle: '#64748b',
          error: '#ef4444',
          warning: '#f59e0b',
          success: '#22c55e',
        },
        // Accent colors
        accent: {
          primary: '#3b82f6',
          secondary: '#8b5cf6',
          teal: '#14b8a6',
          cyan: '#06b6d4',
        },
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'SF Mono', 'Consolas', 'monospace'],
        display: ['"DM Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'blink': 'blink 1s step-end infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(79, 209, 197, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(79, 209, 197, 0.5)' },
        },
        slideUp: {
          '0%': { opacity: 0, transform: 'translateY(10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(to right, rgba(42, 49, 64, 0.3) 1px, transparent 1px), linear-gradient(to bottom, rgba(42, 49, 64, 0.3) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(79, 209, 197, 0.15)',
        'glow-md': '0 0 20px rgba(79, 209, 197, 0.2)',
        'glow-lg': '0 0 30px rgba(79, 209, 197, 0.25)',
        'inner-glow': 'inset 0 1px 2px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
};
