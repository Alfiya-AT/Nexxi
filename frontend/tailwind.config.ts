import type { Config } from 'tailwindcss'
import { fontFamily } from 'tailwindcss/defaultTheme'

const config: Config = {
    darkMode: 'class',
    content: ['./index.html', './src/**/*.{ts,tsx}'],
    theme: {
        extend: {
            colors: {
                nexxi: {
                    'bg-primary': '#0A0A0F',
                    'bg-secondary': '#12121A',
                    'bg-tertiary': '#1A1A28',
                    'accent': '#7C3AED',
                    'accent-light': '#9F7AEA',
                    'cyan': '#06B6D4',
                    'border': '#2D2D3D',
                    'border-light': '#3D3D55',
                    'text-primary': '#F8FAFC',
                    'text-secondary': '#94A3B8',
                    'text-muted': '#475569',
                    'user-bubble': '#7C3AED',
                    'bot-bubble': '#1E1E2E',
                    'success': '#10B981',
                    'error': '#EF4444',
                    'warning': '#F59E0B',
                },
            },
            fontFamily: {
                sans: ['Inter', ...fontFamily.sans],
                mono: ['JetBrains Mono', ...fontFamily.mono],
            },
            backgroundImage: {
                'nexxi-gradient': 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)',
                'nexxi-gradient-v': 'linear-gradient(to bottom, #7C3AED, #06B6D4)',
                'nexxi-radial': 'radial-gradient(ellipse at center, rgba(124,58,237,0.15) 0%, transparent 70%)',
                'grid-pattern': 'linear-gradient(rgba(45,45,61,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(45,45,61,0.3) 1px, transparent 1px)',
            },
            backgroundSize: {
                'grid': '32px 32px',
            },
            boxShadow: {
                'nexxi-glow': '0 0 20px rgba(124,58,237,0.35)',
                'nexxi-glow-lg': '0 0 40px rgba(124,58,237,0.5)',
                'cyan-glow': '0 0 20px rgba(6,182,212,0.35)',
                'card': '0 8px 32px rgba(0,0,0,0.5)',
            },
            animation: {
                'typing-bounce': 'typingBounce 1.4s ease-in-out infinite',
                'glow-pulse': 'glowPulse 2.5s ease-in-out infinite',
                'slide-up': 'slideUp 0.3s ease-out',
                'fade-in': 'fadeIn 0.25s ease-out',
                'spin-slow': 'spin 2s linear infinite',
                'recording-ring': 'recordingRing 1.2s ease-in-out infinite',
                'float': 'float 6s ease-in-out infinite',
                'shimmer': 'shimmer 1.5s infinite',
            },
            keyframes: {
                typingBounce: {
                    '0%, 60%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
                    '30%': { transform: 'translateY(-8px)', opacity: '1' },
                },
                glowPulse: {
                    '0%, 100%': { boxShadow: '0 0 20px rgba(124,58,237,0.3)' },
                    '50%': { boxShadow: '0 0 40px rgba(124,58,237,0.7)' },
                },
                slideUp: {
                    from: { opacity: '0', transform: 'translateY(16px)' },
                    to: { opacity: '1', transform: 'translateY(0)' },
                },
                fadeIn: {
                    from: { opacity: '0' },
                    to: { opacity: '1' },
                },
                recordingRing: {
                    '0%, 100%': { transform: 'scale(1)', opacity: '1', boxShadow: '0 0 0 0 rgba(239,68,68,0.6)' },
                    '50%': { transform: 'scale(1.1)', opacity: '0.8', boxShadow: '0 0 0 10px rgba(239,68,68,0)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-12px)' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}

export default config
