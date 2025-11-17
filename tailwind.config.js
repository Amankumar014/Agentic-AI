/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9f7',
          100: '#d9f2ed',
          200: '#b3e5db',
          300: '#7ec4b6',
          400: '#5ba499',
          500: '#4a9186',
          600: '#3a736d',
          700: '#325d59',
          800: '#2d4c49',
          900: '#28403e',
        },
        secondary: {
          50: '#f5f8fa',
          100: '#e8f0f5',
          200: '#d1e1eb',
          300: '#aac9db',
          400: '#7dadc7',
          500: '#5b92b3',
          600: '#467799',
          700: '#3a607d',
          800: '#335167',
          900: '#2d4456',
        },
        accent: {
          50: '#fef3f2',
          100: '#fee5e2',
          200: '#fecfca',
          300: '#fcada5',
          400: '#f87d71',
          500: '#ef5844',
          600: '#dc3b27',
          700: '#b9301d',
          800: '#992c1c',
          900: '#7f2b1d',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        fadeIn: {
          'from': {
            opacity: '0',
            transform: 'translateY(20px)'
          },
          'to': {
            opacity: '1',
            transform: 'translateY(0)'
          }
        },
        slideUp: {
          'from': {
            opacity: '0',
            transform: 'translateY(30px)'
          },
          'to': {
            opacity: '1',
            transform: 'translateY(0)'
          }
        },
        shimmer: {
          '0%': { left: '-100%' },
          '100%': { left: '100%' }
        }
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'soft-lg': '0 10px 40px -10px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}

