const THEME_STORAGE_KEY = 'tseyor-theme';

export function readThemePreference() {
    if (typeof window === 'undefined') {
        return null;
    }

    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);

    if (savedTheme === 'dark') {
        return true;
    }

    if (savedTheme === 'light') {
        return false;
    }

    return null;
}

export function setThemePreference(darkMode, { persist = true, apply = true } = {}) {
    const enabled = Boolean(darkMode);

    if (persist && typeof window !== 'undefined') {
        window.localStorage.setItem(THEME_STORAGE_KEY, enabled ? 'dark' : 'light');
    }

    if (apply && typeof document !== 'undefined') {
        document.documentElement.classList.toggle('dark', enabled);
        document.documentElement.setAttribute('data-theme', enabled ? 'dark' : 'light');
    }

    return enabled;
}

export function resolveThemePreference(fallback = false) {
    return readThemePreference() ?? Boolean(fallback);
}
