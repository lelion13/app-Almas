/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f4f7fb",
          100: "#e8eef6",
          500: "#3d6b8a",
          700: "#2a4a5f",
          900: "#1a2f3d",
        },
      },
    },
  },
  plugins: [],
};
