/**
 * Theme context — dark/light mode toggle with localStorage persistence.
 * @module ThemeContext
 */
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

/**
 * Theme context — provides dark mode toggle with localStorage persistence.
 *
 * How it works:
 * 1. On mount, reads 'theme' from localStorage (default: 'light')
 * 2. Provides `isDark` and `toggleTheme` to all children
 * 3. `toggleTheme` updates both state and localStorage
 *
 * Ant Design integration:
 * - App.tsx reads `isDark` and sets `theme.darkAlgorithm` or `theme.defaultAlgorithm`
 * - Ant Design re-renders all components with new theme tokens automatically
 */

type ThemeContextType = {
    isDark: boolean;
    toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextType>({
    isDark: false,
    toggleTheme: () => { },
});

const STORAGE_KEY = 'log-analyzer-theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [isDark, setIsDark] = useState(() => {
        // Read initial theme from localStorage
        return localStorage.getItem(STORAGE_KEY) === 'dark';
    });

    useEffect(() => {
        // Persist to localStorage whenever theme changes
        localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');

        // Also set data attribute on <html> for CSS that needs it
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    }, [isDark]);

    const toggleTheme = () => setIsDark((prev) => !prev);

    return (
        <ThemeContext.Provider value={{ isDark, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

/**
 * Hook to access theme state.
 *
 * Usage:
 *   const { isDark, toggleTheme } = useTheme();
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
    return useContext(ThemeContext);
}
