/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        arabic: ['"Cairo"', '"Tajawal"', '"Noto Sans Arabic"', "sans-serif"],
      },
      colors: {
        // لوحة Claude الدافئة
        canvas: "#FAF9F5",
        surface: "#FFFFFF",
        ink: "#191919",
        "ink-soft": "#2B2B2B",
        "ink-muted": "#6B6B6B",
        accent: "#D97757",
        "accent-dark": "#B95F42",
        "accent-soft": "#F5E9E2",
        line: "#E5E3DA",
        "line-soft": "#EFEDE6",
        success: "#3B7A57",
        "success-soft": "#E4EFE8",
        warning: "#B7791F",
        "warning-soft": "#FBF0DC",
        danger: "#A63A2B",
        "danger-soft": "#FAE7E3",
      },
      borderRadius: {
        xl: "12px",
      },
      boxShadow: {
        soft: "0 1px 3px rgba(25, 25, 25, 0.06), 0 1px 2px rgba(25, 25, 25, 0.04)",
        card: "0 2px 8px rgba(25, 25, 25, 0.06)",
      },
    },
  },
  plugins: [],
};
