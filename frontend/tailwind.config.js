/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#151821",
        "surface-2": "#1B1F2A",
        border: "#232833",
        muted: "#9AA1AD",
        accent: { DEFAULT: "#2DD4BF", hover: "#14B8A6" },
        record: "#F43F5E",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
