/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        omega: {
          bg: "#070b14",
          card: "#0f1629",
          border: "#1e2d4a",
          accent: "#3b82f6",
          glow: "#22d3ee",
          muted: "#8b9cb3",
        },
      },
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        display: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
