import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 克莱因蓝（Klein Blue）作为强调色
        klein: {
          DEFAULT: "#002FA7",
          light: "#1a4dd1",
          soft: "#e8edfb",
        },
      },
      backgroundColor: {
        canvas: "#fafafa",
      },
      backdropBlur: {
        xs: "2px",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
