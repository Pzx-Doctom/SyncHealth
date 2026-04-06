/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './App.{js,jsx,ts,tsx}',
    './src/**/*.{js,jsx,ts,tsx}',
    './global.css',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4F46E5',
          light: '#667eea',
          dark: '#3730A3',
        },
        secondary: '#764ba2',
        background: {
          DEFAULT: '#FFFFFF',
          secondary: '#F2F2F7',
          tertiary: '#F9FAFB',
        },
        text: {
          primary: '#1C1C1E',
          secondary: '#8E8E93',
          tertiary: '#AEAEB2',
        },
        success: '#34C759',
        danger: '#FF3B30',
        warning: '#FF9500',
      },
      fontFamily: {
        sans: ['System', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
