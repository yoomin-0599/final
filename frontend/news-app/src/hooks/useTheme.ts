import { useState, useEffect, createContext, useContext } from 'react';
import { createTheme, alpha } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';

// 🎨 컬러 팔레트 정의
const colorPalette = {
  light: {
    primary: {
      main: '#2563eb', // 모던 블루
      light: '#60a5fa',
      dark: '#1d4ed8',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc2626', // 비비드 레드
      light: '#f87171',
      dark: '#b91c1c',
      contrastText: '#ffffff',
    },
    accent: {
      main: '#059669', // 에메랄드
      light: '#34d399',
      dark: '#047857',
    },
    neutral: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
      elevated: '#fefefe',
      sidebar: '#f1f5f9',
    },
    surface: {
      primary: alpha('#2563eb', 0.08),
      secondary: alpha('#dc2626', 0.08),
      accent: alpha('#059669', 0.08),
    }
  },
  dark: {
    primary: {
      main: '#3b82f6', // 밝은 블루
      light: '#60a5fa',
      dark: '#2563eb',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ef4444', // 밝은 레드
      light: '#f87171',
      dark: '#dc2626',
      contrastText: '#ffffff',
    },
    accent: {
      main: '#10b981', // 밝은 에메랄드
      light: '#34d399',
      dark: '#059669',
    },
    neutral: {
      50: '#0f172a',
      100: '#1e293b',
      200: '#334155',
      300: '#475569',
      400: '#64748b',
      500: '#94a3b8',
      600: '#cbd5e1',
      700: '#e2e8f0',
      800: '#f1f5f9',
      900: '#f8fafc',
    },
    background: {
      default: '#0f172a',
      paper: '#1e293b',
      elevated: '#334155',
      sidebar: '#1e293b',
    },
    surface: {
      primary: alpha('#3b82f6', 0.12),
      secondary: alpha('#ef4444', 0.12),
      accent: alpha('#10b981', 0.12),
    }
  }
};

interface ThemeContextType {
  isDarkMode: boolean;
  toggleTheme: () => void;
  theme: Theme;
  colors: typeof colorPalette.light;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const useThemeProvider = () => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('news-theme-preference');
    if (saved) {
      return saved === 'dark';
    }
    // 시스템 다크모드 설정 감지
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // 시스템 다크모드 변경 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      const saved = localStorage.getItem('news-theme-preference');
      if (!saved) {
        setIsDarkMode(e.matches);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    localStorage.setItem('news-theme-preference', isDarkMode ? 'dark' : 'light');
    // HTML 루트 요소에 다크모드 클래스 추가/제거
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(prev => !prev);
  };

  const mode = isDarkMode ? 'dark' : 'light';
  const colors = colorPalette[mode];

  const theme = createTheme({
    palette: {
      mode,
      primary: colors.primary,
      secondary: colors.secondary,
      background: {
        default: colors.background.default,
        paper: colors.background.paper,
      },
      text: {
        primary: isDarkMode ? colors.neutral[800] : colors.neutral[800],
        secondary: isDarkMode ? colors.neutral[600] : colors.neutral[500],
      },
      divider: isDarkMode ? colors.neutral[200] : colors.neutral[200],
      action: {
        hover: alpha(colors.primary.main, 0.04),
        selected: alpha(colors.primary.main, 0.08),
        disabled: alpha(colors.neutral[400], 0.38),
        disabledBackground: alpha(colors.neutral[400], 0.12),
      },
      // 커스텀 컬러 팔레트 추가
      ...({
        accent: colors.accent,
        neutral: colors.neutral,
        surface: colors.surface,
      } as any),
    },
    typography: {
      fontFamily: '"Pretendard", "Inter", "Roboto", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif',
      h1: {
        fontSize: '2.5rem',
        fontWeight: 700,
        lineHeight: 1.2,
        letterSpacing: '-0.02em',
      },
      h2: {
        fontSize: '2rem',
        fontWeight: 700,
        lineHeight: 1.3,
        letterSpacing: '-0.01em',
      },
      h3: {
        fontSize: '1.75rem',
        fontWeight: 600,
        lineHeight: 1.3,
      },
      h4: {
        fontSize: '1.5rem',
        fontWeight: 600,
        lineHeight: 1.4,
      },
      h5: {
        fontSize: '1.25rem',
        fontWeight: 600,
        lineHeight: 1.4,
      },
      h6: {
        fontSize: '1.125rem',
        fontWeight: 600,
        lineHeight: 1.4,
      },
      subtitle1: {
        fontSize: '1rem',
        fontWeight: 500,
        lineHeight: 1.5,
      },
      subtitle2: {
        fontSize: '0.875rem',
        fontWeight: 500,
        lineHeight: 1.5,
      },
      body1: {
        fontSize: '1rem',
        lineHeight: 1.6,
      },
      body2: {
        fontSize: '0.875rem',
        lineHeight: 1.6,
      },
      caption: {
        fontSize: '0.75rem',
        lineHeight: 1.4,
        color: colors.neutral[500],
      },
    },
    shape: {
      borderRadius: 12,
    },
    shadows: isDarkMode ? [
      'none',
      '0px 1px 2px rgba(0, 0, 0, 0.24)',
      '0px 1px 4px rgba(0, 0, 0, 0.24)',
      '0px 2px 6px rgba(0, 0, 0, 0.24)',
      '0px 2px 8px rgba(0, 0, 0, 0.24)',
      '0px 4px 12px rgba(0, 0, 0, 0.24)',
      '0px 4px 16px rgba(0, 0, 0, 0.24)',
      '0px 6px 20px rgba(0, 0, 0, 0.24)',
      '0px 6px 24px rgba(0, 0, 0, 0.24)',
      '0px 8px 28px rgba(0, 0, 0, 0.24)',
      '0px 8px 32px rgba(0, 0, 0, 0.24)',
      '0px 10px 36px rgba(0, 0, 0, 0.24)',
      '0px 10px 40px rgba(0, 0, 0, 0.24)',
      '0px 12px 44px rgba(0, 0, 0, 0.24)',
      '0px 12px 48px rgba(0, 0, 0, 0.24)',
      '0px 14px 52px rgba(0, 0, 0, 0.24)',
      '0px 14px 56px rgba(0, 0, 0, 0.24)',
      '0px 16px 60px rgba(0, 0, 0, 0.24)',
      '0px 16px 64px rgba(0, 0, 0, 0.24)',
      '0px 18px 68px rgba(0, 0, 0, 0.24)',
      '0px 18px 72px rgba(0, 0, 0, 0.24)',
      '0px 20px 76px rgba(0, 0, 0, 0.24)',
      '0px 20px 80px rgba(0, 0, 0, 0.24)',
      '0px 22px 84px rgba(0, 0, 0, 0.24)',
      '0px 22px 88px rgba(0, 0, 0, 0.24)',
    ] : [
      'none',
      '0px 1px 2px rgba(0, 0, 0, 0.05)',
      '0px 1px 4px rgba(0, 0, 0, 0.08)',
      '0px 2px 6px rgba(0, 0, 0, 0.1)',
      '0px 2px 8px rgba(0, 0, 0, 0.12)',
      '0px 4px 12px rgba(0, 0, 0, 0.15)',
      '0px 4px 16px rgba(0, 0, 0, 0.15)',
      '0px 6px 20px rgba(0, 0, 0, 0.15)',
      '0px 6px 24px rgba(0, 0, 0, 0.15)',
      '0px 8px 28px rgba(0, 0, 0, 0.15)',
      '0px 8px 32px rgba(0, 0, 0, 0.15)',
      '0px 10px 36px rgba(0, 0, 0, 0.15)',
      '0px 10px 40px rgba(0, 0, 0, 0.15)',
      '0px 12px 44px rgba(0, 0, 0, 0.15)',
      '0px 12px 48px rgba(0, 0, 0, 0.15)',
      '0px 14px 52px rgba(0, 0, 0, 0.15)',
      '0px 14px 56px rgba(0, 0, 0, 0.15)',
      '0px 16px 60px rgba(0, 0, 0, 0.15)',
      '0px 16px 64px rgba(0, 0, 0, 0.15)',
      '0px 18px 68px rgba(0, 0, 0, 0.15)',
      '0px 18px 72px rgba(0, 0, 0, 0.15)',
      '0px 20px 76px rgba(0, 0, 0, 0.15)',
      '0px 20px 80px rgba(0, 0, 0, 0.15)',
      '0px 22px 84px rgba(0, 0, 0, 0.15)',
      '0px 22px 88px rgba(0, 0, 0, 0.15)',
    ],
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            transition: 'background-color 0.3s ease, color 0.3s ease',
            scrollbarWidth: 'thin',
            scrollbarColor: `${colors.neutral[300]} ${colors.background.default}`,
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              background: colors.background.default,
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: colors.neutral[300],
              borderRadius: '4px',
              '&:hover': {
                backgroundColor: colors.neutral[400],
              },
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 16,
            border: `1px solid ${alpha(colors.neutral[200], 0.8)}`,
            transition: 'box-shadow 0.2s ease, transform 0.2s ease',
            '&:hover': {
              boxShadow: isDarkMode 
                ? '0 8px 32px rgba(0, 0, 0, 0.32)'
                : '0 8px 32px rgba(0, 0, 0, 0.12)',
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            textTransform: 'none',
            fontWeight: 600,
            boxShadow: 'none',
            '&:hover': {
              boxShadow: 'none',
            },
          },
          containedPrimary: {
            background: `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.primary.dark} 100%)`,
            '&:hover': {
              background: `linear-gradient(135deg, ${colors.primary.dark} 0%, ${colors.primary.main} 100%)`,
            },
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            fontSize: '0.95rem',
            fontWeight: 600,
            textTransform: 'none',
            borderRadius: '8px 8px 0 0',
            margin: '0 2px',
            minHeight: '48px',
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: {
            height: '3px',
            borderRadius: '2px',
            background: `linear-gradient(90deg, ${colors.primary.main}, ${colors.secondary.main})`,
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            fontWeight: 500,
          },
          outlined: {
            borderColor: alpha(colors.primary.main, 0.3),
            '&:hover': {
              backgroundColor: colors.surface.primary,
              borderColor: colors.primary.main,
            },
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            background: isDarkMode 
              ? `linear-gradient(135deg, ${colors.background.paper} 0%, ${colors.background.elevated} 100%)`
              : `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.primary.dark} 100%)`,
            backdropFilter: 'blur(10px)',
            borderBottom: `1px solid ${alpha(colors.neutral[200], 0.2)}`,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: colors.background.sidebar,
            borderRight: `1px solid ${alpha(colors.neutral[200], 0.12)}`,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: 12,
              '& fieldset': {
                borderColor: alpha(colors.neutral[300], 0.5),
              },
              '&:hover fieldset': {
                borderColor: colors.primary.main,
              },
              '&.Mui-focused fieldset': {
                borderColor: colors.primary.main,
              },
            },
          },
        },
      },
    },
  });

  return { isDarkMode, toggleTheme, theme, colors, ThemeContext };
};
