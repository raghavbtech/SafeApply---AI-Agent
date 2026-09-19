/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        heading: ['Poppins', 'sans-serif'],
        poppins: ['Poppins', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        surface: {
          deep: '#06090F',
          card: '#0B0F19',
          cardHover: '#101626',
          raised: '#101626',
          border: '#1E293B',
          subtle: '#161F36',
        },
        'surface-card': '#0B0F19',
        'surface-raised': '#101626',
        'surface-border': '#1E293B',
        'border-subtle': 'rgba(255, 255, 255, 0.08)',
        'border-medium': 'rgba(255, 255, 255, 0.16)',
        dark: {
          950: '#06090F',
          900: '#0B0F19',
          850: '#101626',
          800: '#161F36',
          700: '#233052',
          600: '#334155',
        },
        neon: {
          cyan: '#06B6D4',
          'cyan-glow': '#22D3EE',
          violet: '#8B5CF6',
          'violet-glow': '#A78BFA',
          pink: '#EC4899',
          emerald: '#10B981',
          amber: '#F59E0B',
          rose: '#EF4444',
        }
      },
      boxShadow: {
        'neon-cyan': '0 0 20px -5px rgba(6, 182, 212, 0.4)',
        'neon-violet': '0 0 20px -5px rgba(139, 92, 246, 0.4)',
        'neon-rose': '0 0 20px -5px rgba(239, 68, 68, 0.4)',
        'neon-emerald': '0 0 20px -5px rgba(16, 185, 129, 0.4)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}
