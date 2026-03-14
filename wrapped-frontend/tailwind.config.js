/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Synesthesia colors
        'syn-columbia-blue': '#9BDDFF',
        'syn-dark-green': '#006400',
        'syn-blue': '#0000FF',
        'syn-red': '#FF0000',
        'syn-yellow': '#FFFF00',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
