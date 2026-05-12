<script lang="ts">
  import { onMount } from 'svelte';

  const STORAGE_KEY = 'flipcommons-theme';

  const themes = [
    { id: 'system', label: 'Current' },
    { id: 'current-v2', label: 'Current v2' },
    { id: 'flyer-archive', label: 'Pinball Flyer Archive' },
    { id: 'score-reel', label: 'Score Reel' },
    { id: 'operators-log', label: "Operator's Log" },
    { id: 'backglass-glow', label: 'Backglass Glow' },
  ] as const;

  type ThemeId = (typeof themes)[number]['id'];

  let selectedTheme = $state<ThemeId>('system');

  function isThemeId(value: string): value is ThemeId {
    return themes.some((theme) => theme.id === value);
  }

  function applyTheme(theme: ThemeId) {
    selectedTheme = theme;

    if (theme === 'system') {
      delete document.documentElement.dataset.theme;
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
  }

  function handleChange(event: Event) {
    const target = event.currentTarget;
    if (!(target instanceof HTMLSelectElement)) return;
    if (isThemeId(target.value)) applyTheme(target.value);
  }

  onMount(() => {
    const storedTheme = localStorage.getItem(STORAGE_KEY);
    if (storedTheme && isThemeId(storedTheme)) {
      applyTheme(storedTheme);
    } else if (storedTheme) {
      localStorage.removeItem(STORAGE_KEY);
    }
  });
</script>

<div class="theme-switcher">
  <label for="theme-select">Theme</label>
  <select id="theme-select" value={selectedTheme} onchange={handleChange}>
    {#each themes as theme (theme.id)}
      <option value={theme.id}>{theme.label}</option>
    {/each}
  </select>
</div>

<style>
  .theme-switcher {
    display: flex;
    align-items: center;
    gap: var(--size-2);
  }

  label {
    color: var(--color-text-muted);
    font-size: var(--font-size-1);
    font-weight: 600;
  }

  select {
    min-width: 10rem;
  }
</style>
