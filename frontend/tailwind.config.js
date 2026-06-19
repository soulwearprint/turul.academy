/** @type {import('tailwindcss').Config} */
// Turul design system — sourced from "Turul Study Companion · Product Vision & UI Design System"
// Primary Blue #2563EB · Secondary Green #22C55E · Accent Amber #F59E0B · Error Red #EF4444
// Type: Inter (body) / Manrope (display). Radius scale: 8 / 12 / 16. Friendly, modern, calm.
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand blue scale (anchored on #2563EB)
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Semantic brand tokens
        turul: {
          blue:   '#2563EB',
          green:  '#22C55E',
          amber:  '#F59E0B',
          gold:   '#F59E0B', // alias kept for existing references
          red:    '#EF4444',
          purple: '#8B5CF6',
          ink:    '#0F172A',
        },
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        // Doc-specified radius system
        sm:  '8px',
        md:  '12px',
        lg:  '16px',
        xl:  '20px',
        '2xl': '24px',
        '3xl': '32px',
      },
      boxShadow: {
        soft:    '0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.06)',
        card:    '0 1px 3px rgba(15, 23, 42, 0.05), 0 8px 24px rgba(15, 23, 42, 0.05)',
        lift:    '0 8px 30px rgba(37, 99, 235, 0.18)',
        'glow-blue': '0 10px 40px rgba(37, 99, 235, 0.28)',
      },
      keyframes: {
        float:  { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-6px)' } },
        blink:  { '0%,90%,100%': { transform: 'scaleY(1)' }, '95%': { transform: 'scaleY(0.1)' } },
        pop:    { '0%': { transform: 'scale(0.85)', opacity: '0' }, '100%': { transform: 'scale(1)', opacity: '1' } },
        wiggle: { '0%,100%': { transform: 'rotate(-3deg)' }, '50%': { transform: 'rotate(3deg)' } },
        'fade-up': { '0%': { transform: 'translateY(10px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        sparkle: { '0%,100%': { transform: 'scale(0.6)', opacity: '0.3' }, '50%': { transform: 'scale(1)', opacity: '1' } },
      },
      animation: {
        float:   'float 3.4s ease-in-out infinite',
        blink:   'blink 4.5s ease-in-out infinite',
        pop:     'pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
        wiggle:  'wiggle 0.5s ease-in-out',
        'fade-up': 'fade-up 0.5s ease-out both',
        sparkle: 'sparkle 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
