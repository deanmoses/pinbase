<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();
</script>

<div class="menu-section-header">
  {@render children()}
</div>

<style>
  /* Same density hooks as MenuItem so a parent can scale headers + items
     together via inheritance. */
  .menu-section-header {
    padding: var(--menu-item-padding, var(--size-1) var(--size-3));
    font-size: var(--menu-section-header-font-size, 0.8rem);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    user-select: none;
  }
</style>
