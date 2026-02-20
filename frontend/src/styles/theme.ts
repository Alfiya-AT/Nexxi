// Nexxi Design System — Brand Tokens
// Single source of truth for all design values

export const theme = {
    colors: {
        bg: {
            primary: '#0A0A0F',
            secondary: '#12121A',
            tertiary: '#1A1A28',
        },
        accent: {
            primary: '#7C3AED',
            light: '#9F7AEA',
            secondary: '#06B6D4',
        },
        text: {
            primary: '#F8FAFC',
            secondary: '#94A3B8',
            muted: '#475569',
        },
        border: '#2D2D3D',
        borderLight: '#3D3D55',
        bubble: {
            user: '#7C3AED',
            bot: '#1E1E2E',
        },
        status: {
            success: '#10B981',
            error: '#EF4444',
            warning: '#F59E0B',
        },
    },

    gradients: {
        nexxi: 'linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%)',
        nexxiV: 'linear-gradient(180deg, #7C3AED 0%, #06B6D4 100%)',
        user: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
    },

    shadows: {
        glow: '0 0 20px rgba(124, 58, 237, 0.35)',
        glowLg: '0 0 40px rgba(124, 58, 237, 0.55)',
        cyan: '0 0 20px rgba(6, 182, 212, 0.35)',
        card: '0 8px 32px rgba(0, 0, 0, 0.5)',
    },

    effects: {
        glass: 'backdrop-filter: blur(12px)',
        glassHeavy: 'backdrop-filter: blur(24px)',
    },

    fonts: {
        sans: '"Inter", system-ui, sans-serif',
        mono: '"JetBrains Mono", "Fira Code", monospace',
    },

    radius: {
        sm: '6px',
        md: '12px',
        lg: '18px',
        xl: '24px',
        full: '9999px',
    },

    animation: {
        fast: '150ms ease',
        normal: '250ms ease',
        slow: '400ms ease',
    },
} as const

export type Theme = typeof theme
