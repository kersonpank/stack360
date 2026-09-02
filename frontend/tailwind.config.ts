import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a1a",
        paper: "#f5f0e8",
        panel: "#fffaf1",
        muted: "#e8e3da",
        yellow: "#ffcc00",
        red: "#e63b2e",
        blue: "#0055ff",
        green: "#00a85a",
      },
      boxShadow: {
        brutal: "5px 5px 0 0 #1a1a1a",
        "brutal-sm": "3px 3px 0 0 #1a1a1a",
        "brutal-blue": "4px 4px 0 0 #0055ff",
      },
      fontFamily: {
        headline: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "2px",
        md: "4px",
      },
    },
  },
  plugins: [],
};

export default config;
