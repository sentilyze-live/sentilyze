import React, { useEffect, useState } from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';

type Theme = 'dark' | 'light' | 'system';

interface ThemeSwitcherProps {
  className?: string;
}

const ThemeSwitcher: React.FC<ThemeSwitcherProps> = ({ className = '' }) => {
  const [theme, setTheme] = useState<Theme>('dark');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const savedTheme = localStorage.getItem('sentilyze-theme') as Theme;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    }
  }, []);

  const applyTheme = (newTheme: Theme) => {
    const root = document.documentElement;
    
    if (newTheme === 'dark') {
      root.classList.remove('light');
      root.style.colorScheme = 'dark';
    } else if (newTheme === 'light') {
      root.classList.add('light');
      root.style.colorScheme = 'light';
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        root.classList.remove('light');
        root.style.colorScheme = 'dark';
      } else {
        root.classList.add('light');
        root.style.colorScheme = 'light';
      }
    }
  };

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    localStorage.setItem('sentilyze-theme', newTheme);
    applyTheme(newTheme);
  };

  if (!mounted) {
    return <div className="h-10 w-32 bg-[var(--bg-tertiary)] rounded-lg animate-pulse" />;
  }

  return (
    <div className={`flex items-center gap-1 p-1 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-color)] ${className}`}>
      <button
        onClick={() => handleThemeChange('light')}
        className={`p-2 rounded-md transition-all duration-200 ${
          theme === 'light'
            ? 'bg-[var(--gold-primary)] text-[var(--bg-primary)] shadow-md'
            : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
        }`}
        aria-label="Açık tema"
        title="Açık tema"
      >
        <Sun className="w-4 h-4" />
      </button>
      
      <button
        onClick={() => handleThemeChange('dark')}
        className={`p-2 rounded-md transition-all duration-200 ${
          theme === 'dark'
            ? 'bg-[var(--gold-primary)] text-[var(--bg-primary)] shadow-md'
            : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
        }`}
        aria-label="Koyu tema"
        title="Koyu tema"
      >
        <Moon className="w-4 h-4" />
      </button>
      
      <button
        onClick={() => handleThemeChange('system')}
        className={`p-2 rounded-md transition-all duration-200 ${
          theme === 'system'
            ? 'bg-[var(--gold-primary)] text-[var(--bg-primary)] shadow-md'
            : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
        }`}
        aria-label="Sistem teması"
        title="Sistem teması"
      >
        <Monitor className="w-4 h-4" />
      </button>
    </div>
  );
};

export default ThemeSwitcher;
