/**
 * SafeApply Design System Tokens
 * Dark Neon theme palette with cyber-security aesthetics.
 */

export const THEME_TOKENS = {
  colors: {
    bg: {
      deep: '#06090F',
      card: '#0B0F19',
      cardHover: '#101626',
      subtle: '#161F36',
    },
    neon: {
      cyan: '#06B6D4',
      cyanGlow: 'rgba(6, 182, 212, 0.4)',
      violet: '#8B5CF6',
      violetGlow: 'rgba(139, 92, 246, 0.4)',
      pink: '#EC4899',
      pinkGlow: 'rgba(236, 72, 153, 0.4)',
      emerald: '#10B981',
      emeraldGlow: 'rgba(16, 185, 129, 0.4)',
      amber: '#F59E0B',
      amberGlow: 'rgba(245, 158, 11, 0.4)',
      rose: '#EF4444',
      roseGlow: 'rgba(239, 68, 68, 0.4)',
    },
    text: {
      primary: '#F8FAFC',
      secondary: '#94A3B8',
      muted: '#64748B',
    },
    border: {
      subtle: 'rgba(255, 255, 255, 0.07)',
      medium: 'rgba(255, 255, 255, 0.15)',
      active: 'rgba(6, 182, 212, 0.5)',
    }
  },
  riskBadges: {
    Critical: {
      bg: 'rgba(239, 68, 68, 0.15)',
      border: '#EF4444',
      text: '#F87171',
      glow: '0 0 12px rgba(239, 68, 68, 0.35)',
    },
    High: {
      bg: 'rgba(239, 68, 68, 0.12)',
      border: 'rgba(239, 68, 68, 0.6)',
      text: '#EF4444',
      glow: '0 0 10px rgba(239, 68, 68, 0.25)',
    },
    Medium: {
      bg: 'rgba(245, 158, 11, 0.12)',
      border: '#F59E0B',
      text: '#FBBF24',
      glow: '0 0 10px rgba(245, 158, 11, 0.25)',
    },
    Low: {
      bg: 'rgba(16, 185, 129, 0.12)',
      border: '#10B981',
      text: '#34D399',
      glow: '0 0 10px rgba(16, 185, 129, 0.25)',
    },
    Neutral: {
      bg: 'rgba(148, 163, 184, 0.1)',
      border: 'rgba(148, 163, 184, 0.3)',
      text: '#94A3B8',
      glow: 'none',
    },
  }
};
