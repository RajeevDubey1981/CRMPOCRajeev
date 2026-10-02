import defaultTheme from "tailwindcss/defaultTheme";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Lato", ...defaultTheme.fontFamily.sans],
      },
      colors: {
        brand: {
          50: "#eff6ff",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        // INDcool brand colours (taken from indcool.in and the INDcool logo)
        indcool: {
          navy: "#1E3A78",
          blue: "#2F5BB5",
          lime: "#B8D828",
          teal: "#DCEEEE",
          red: "#D64545",
          text: "#212529",
        },
      },
    },
  },
  plugins: [],
};
