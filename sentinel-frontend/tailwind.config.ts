import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        clinical: {
          dark: "#0b132b",
          card: "#1c2541",
          border: "#3a506b",
          accent: "#48cae4",
          danger: "#e63946",
          warning: "#ffb703",
          success: "#2a9d8f",
        },
      },
    },
  },
  plugins: [],
};
export default config;
