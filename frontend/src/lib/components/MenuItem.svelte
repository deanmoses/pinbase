<script lang="ts">
  import { getContext, type Snippet } from 'svelte';

  let {
    href = undefined,
    onclick = undefined,
    disabled = false,
    current = false,
    children,
  }: {
    href?: string;
    onclick?: () => void;
    disabled?: boolean;
    current?: boolean;
    children: Snippet;
  } = $props();

  const parentRole = getContext<'menu' | 'listbox'>('action-menu-role') ?? 'menu';
  const itemRole = parentRole === 'listbox' ? 'option' : 'menuitem';
  const ariaSelected = $derived(parentRole === 'listbox' ? current : undefined);
</script>

{#if disabled}
  <span
    class:current
    class="menu-item disabled"
    role={itemRole}
    aria-disabled="true"
    aria-selected={ariaSelected}
    tabindex="-1"
  >
    {@render children()}
  </span>
{:else if href}
  <a class="menu-item" {href} role={itemRole} aria-selected={ariaSelected} tabindex="-1">
    {@render children()}
  </a>
{:else}
  <button
    class:current
    class="menu-item"
    type="button"
    role={itemRole}
    aria-selected={ariaSelected}
    tabindex="-1"
    {onclick}
  >
    {@render children()}
  </button>
{/if}

<style>
  .menu-item {
    display: block;
    width: 100%;
    padding: var(--size-1) var(--size-3);
    font-size: var(--font-size-0);
    font-family: inherit;
    color: var(--color-text-primary);
    text-decoration: none;
    background: none;
    border: none;
    cursor: pointer;
    text-align: start;
    white-space: nowrap;
  }

  .menu-item:hover,
  .menu-item:focus-visible {
    background: var(--color-surface);
    color: var(--color-accent);
  }

  .menu-item.current {
    font-weight: 600;
  }

  .menu-item.current::before {
    content: '✓ ';
  }

  .menu-item.disabled {
    cursor: default;
    color: var(--color-text-muted);
  }

  .menu-item.disabled:hover {
    background: none;
    color: var(--color-text-muted);
  }

  .menu-item:focus-visible {
    outline: none;
  }
</style>
