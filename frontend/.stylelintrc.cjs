/**
 * Stylelint config — guards token discipline in component <style> blocks.
 *
 * Enforces:
 *   - @media queries use only the project's --breakpoint-* custom media
 *     (and prefers-color-scheme); raw min-width/max-width is rejected.
 *   - No raw hex / rgb / rgba / hsl / hsla colors in components — use the
 *     --color-* tokens defined in src/app.css.
 *   - No :global selectors (project rule; inline-disable is the escape hatch).
 *   - No !important.
 *
 * The `overrides` block at the bottom is a baseline: existing files with
 * pre-stylelint violations are listed there with the offending rules disabled.
 * Cleanup PRs remove entries from the list one file at a time. Analogous to
 * backend/mypy-baseline.txt.
 */

module.exports = {
  // Hand-picked rules only — stylelint-config-standard enforces too much
  // stylistic noise (hex shortening, modern color notation, alpha %,
  // descending-specificity, etc.) that this project doesn't care about.
  rules: {
    // ---- Token discipline ----
    'color-no-hex': true,
    'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla'],
    'media-feature-name-allowed-list': [
      '--breakpoint-narrow',
      '--breakpoint-wide',
      'prefers-color-scheme',
    ],
    // ---- Project rules ----
    'selector-pseudo-class-disallowed-list': ['global'],
    'declaration-no-important': true,
    // ---- Free correctness wins ----
    'declaration-block-no-duplicate-properties': true,
    'declaration-block-no-shorthand-property-overrides': true,
    'no-duplicate-at-import-rules': true,
    'no-invalid-position-at-import-rule': true,
    'block-no-empty': true,
    'no-empty-source': null, // empty <style> blocks are fine in Svelte
  },
  overrides: [
    {
      files: ['**/*.svelte'],
      customSyntax: 'postcss-html',
    },
    // ---- Baseline ----
    // app.css defines the design tokens; raw hex/rgba inside :root blocks is
    // the source of truth and exempt from the no-color rules.
    {
      files: ['src/app.css'],
      rules: {
        'color-no-hex': null,
        'function-disallowed-list': null,
      },
    },
    // Components with deliberate :global usage (rendered HTML from
    // external sources). These are exceptions, not cleanup targets.
    {
      files: ['src/lib/components/Markdown.svelte', 'src/routes/(legal)/+layout.svelte'],
      rules: {
        'selector-pseudo-class-disallowed-list': null,
      },
    },
    // Components with pre-stylelint hex/rgb violations. Remove entries as
    // each file is cleaned up.
    {
      files: [
        'src/lib/toast/ToastHost.svelte',
        'src/lib/components/Modal.svelte',
        'src/lib/components/Avatar.svelte',
        'src/lib/components/CitationTooltip.svelte',
        'src/lib/components/ChipGroup.svelte',
        'src/lib/components/Button.svelte',
        'src/lib/components/FilterDrawer.svelte',
        'src/lib/components/HeroHeader.svelte',
        'src/lib/components/Markdown.svelte',
        'src/lib/components/SearchableSelect.svelte',
        'src/lib/components/ManufacturerActiveFilterChips.svelte',
        'src/lib/components/ActionMenu.svelte',
        'src/lib/components/Nav.svelte',
        'src/lib/components/ActiveFilterChips.svelte',
        'src/lib/components/form/MarkdownTextArea.svelte',
        'src/lib/components/cards/WearEffect.svelte',
        'src/lib/components/cards/Card.svelte',
        'src/lib/components/media/MediaLightbox.svelte',
        'src/lib/components/media/MediaCard.svelte',
        'src/lib/kiosk/KioskHome.svelte',
        'src/routes/+page.svelte',
        'src/routes/kiosk/configure/+page.svelte',
      ],
      rules: {
        'color-no-hex': null,
        'function-disallowed-list': null,
      },
    },
  ],
  ignoreFiles: ['build/**', '.svelte-kit/**', 'node_modules/**', 'src/lib/api/schema.d.ts'],
};
