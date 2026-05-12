/**
 * Theme registry. Each non-default theme's tokens live in its own CSS file
 * and are loaded on demand via a dynamic import — Vite code-splits each
 * file into its own asset, so unused themes cost nothing on first paint.
 *
 * `system` means "no override": delete the `data-theme` attribute and the
 * default light/dark tokens in app.css take over via `prefers-color-scheme`.
 */
export interface Theme {
  id: string;
  label: string;
  /** Dynamic import of the theme's CSS (no-op for `system`). */
  load: () => Promise<unknown>;
}

const noop = () => Promise.resolve();

export const THEMES = [
  { id: 'system', label: 'Current', load: noop },
  {
    id: 'original-light',
    label: 'Original - Light',
    load: () => import('./original-light.css'),
  },
  {
    id: 'original-dark',
    label: 'Original - Dark',
    load: () => import('./original-dark.css'),
  },
  {
    id: 'original-v2-light',
    label: 'Original v2 - Light',
    load: () => import('./original-v2-light.css'),
  },
  {
    id: 'original-v2-dark',
    label: 'Original v2 - Dark',
    load: () => import('./original-v2-dark.css'),
  },
  {
    id: 'flyer-archive-light',
    label: 'Pinball Flyer Archive - Light',
    load: () => import('./flyer-archive-light.css'),
  },
  {
    id: 'flyer-archive-dark',
    label: 'Pinball Flyer Archive - Dark',
    load: () => import('./flyer-archive-dark.css'),
  },
  {
    id: 'score-reel-light',
    label: 'Score Reel - Light',
    load: () => import('./score-reel-light.css'),
  },
  {
    id: 'score-reel-dark',
    label: 'Score Reel - Dark',
    load: () => import('./score-reel-dark.css'),
  },
  {
    id: 'score-reel-2-light',
    label: 'Score Reel 2 - Light',
    load: () => import('./score-reel-2-light.css'),
  },
  {
    id: 'score-reel-2-dark',
    label: 'Score Reel 2 - Dark',
    load: () => import('./score-reel-2-dark.css'),
  },
  {
    id: 'score-reel-3-light',
    label: 'Score Reel 3 - Light',
    load: () => import('./score-reel-3-light.css'),
  },
  {
    id: 'score-reel-3-dark',
    label: 'Score Reel 3 - Dark',
    load: () => import('./score-reel-3-dark.css'),
  },
  {
    id: 'operators-log-light',
    label: "Operator's Log - Light",
    load: () => import('./operators-log-light.css'),
  },
  {
    id: 'operators-log-dark',
    label: "Operator's Log - Dark",
    load: () => import('./operators-log-dark.css'),
  },
  {
    id: 'backglass-glow-dark',
    label: 'Backglass Glow - Dark',
    load: () => import('./backglass-glow-dark.css'),
  },
] as const satisfies readonly Theme[];

// Fail fast at module load if a copy-paste leaves two entries with the
// same id — TS's `as const satisfies` can't catch this.
{
  const ids = THEMES.map((t) => t.id);
  if (new Set(ids).size !== ids.length) {
    throw new Error(`Duplicate theme id in THEMES: ${ids.join(', ')}`);
  }
}

export type ThemeId = (typeof THEMES)[number]['id'];

const LEGACY_THEME_IDS: Record<string, ThemeId> = {
  'current-v2-light': 'original-v2-light',
  'current-v2-dark': 'original-v2-dark',
};

export function isThemeId(value: string): value is ThemeId {
  return THEMES.some((t) => t.id === value);
}

export function normalizeThemeId(value: string): ThemeId | null {
  if (isThemeId(value)) return value;
  return LEGACY_THEME_IDS[value] ?? null;
}

export function getTheme(id: ThemeId): Theme {
  const theme = THEMES.find((t) => t.id === id);
  if (!theme) throw new Error(`Unknown theme: ${id}`);
  return theme;
}

export const THEME_STORAGE_KEY = 'flipcommons-theme';

/**
 * Apply a persisted theme on app boot. Themes are a dev/UX playground —
 * any failure here (localStorage blocked, CSS chunk 404, unknown id) MUST
 * leave the site rendering the default palette rather than break the page.
 * Catches everything and swallows it. A brief flash before the chunk loads
 * is acceptable since themes are test-only.
 */
export async function bootstrapTheme(): Promise<void> {
  try {
    const stored = safeGetItem(THEME_STORAGE_KEY);
    if (!stored) return;
    const theme = normalizeThemeId(stored);
    if (!theme || theme === 'system') {
      safeRemoveItem(THEME_STORAGE_KEY);
      return;
    }
    await getTheme(theme).load();
    document.documentElement.dataset.theme = theme;
    if (theme !== stored) safeSetItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Default palette is already rendering; nothing to undo.
  }
}

/* localStorage wrappers: access can throw (Safari "Block All Cookies",
   sandboxed iframes, quota exhaustion). Callers treat failure as "no
   stored theme" and continue with the default. */
function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
