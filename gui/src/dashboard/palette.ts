export const COLORS = {
  bg: '#0a0e1a',
  surface: '#111827',
  border: '#1e293b',
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  text: '#f1f5f9',
  muted: '#64748b',
}

export const CATEGORICAL = [
  COLORS.primary,
  COLORS.success,
  COLORS.warning,
  COLORS.danger,
  '#a855f7',
  '#06b6d4',
]

export const DIFFICULTY_COLOR: Record<string, string> = {
  easy: COLORS.success,
  medium: COLORS.primary,
  hard: COLORS.warning,
}

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderRadius: 8,
    color: COLORS.text,
    fontSize: 12,
  },
  labelStyle: { color: COLORS.muted },
  itemStyle: { color: COLORS.text },
} as const
