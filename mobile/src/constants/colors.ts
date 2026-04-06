// SyncHealth 品牌色系
export const Colors = {
  // 主色系
  primary: '#4F46E5',
  primaryLight: '#667eea',
  primaryDark: '#3730A3',
  secondary: '#764ba2',

  // 渐变
  gradientStart: '#667eea',
  gradientEnd: '#764ba2',

  // 背景色
  bgPrimary: '#FFFFFF',
  bgSecondary: '#F2F2F7',
  bgTertiary: '#F9FAFB',

  // 文字色
  textPrimary: '#1C1C1E',
  textSecondary: '#8E8E93',
  textTertiary: '#AEAEB2',

  // 功能色
  success: '#34C759',
  danger: '#FF3B30',
  warning: '#FF9500',

  // 分割线
  separator: '#E5E5EA',
  border: '#D1D5DB',
} as const;

// iOS 风格间距
export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

// 圆角
export const BorderRadius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 9999,
} as const;
