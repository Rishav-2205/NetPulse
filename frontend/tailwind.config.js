/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#090d13',
          card: '#161b22',
          header: '#0d1117',
          border: '#30363d',
          hover: '#21262d',
          text: '#c9d1d9',
          muted: '#8b949e',
          heading: '#f0f6fc',
        },
        netpulse: {
          blue: '#58a6ff',
          green: '#2ea043',
          red: '#da3633',
          yellow: '#d29922',
          purple: '#bc8cff',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
