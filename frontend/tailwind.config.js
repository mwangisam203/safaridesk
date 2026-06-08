/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        paper: "#f7f8f5",
        green: {
          50: "#eef8f1",
          100: "#d8efde",
          500: "#2e8b57",
          600: "#227447",
          700: "#185d38"
        },
        coral: "#e76245",
        sun: "#f0b429",
        cobalt: "#315fc4"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Newsreader", "Georgia", "serif"]
      },
      boxShadow: {
        soft: "0 14px 34px rgba(23, 33, 27, 0.08)"
      }
    }
  },
  plugins: []
};
