<script lang="ts">
  import type { Snippet } from 'svelte';
  import { resolveHref } from '$lib/utils';

  let {
    href,
    children,
    actions,
  }: {
    href?: string;
    children: Snippet;
    actions?: Snippet;
  } = $props();
</script>

<li class="row">
  {#if href}
    <a href={resolveHref(href)} class="content content--link">{@render children()}</a>
  {:else}
    <div class="content">{@render children()}</div>
  {/if}
  {#if actions}
    <div class="actions">{@render actions()}</div>
  {/if}
</li>

<style>
  .row {
    display: flex;
    flex-direction: column;
    gap: var(--size-3);
    padding: var(--size-3) 0;
    border-bottom: 1px solid var(--color-border-soft);
  }
  .row:last-child {
    border-bottom: none;
  }
  .content {
    display: flex;
    align-items: baseline;
    gap: var(--size-3);
    min-width: 0;
    color: var(--color-text);
  }
  .content--link {
    text-decoration: none;
  }
  .content--link:hover {
    color: var(--color-link);
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: var(--size-2);
  }

  @media (--breakpoint-wide) {
    .row {
      flex-direction: row;
      align-items: center;
    }
    .content {
      flex: 1;
    }
    .actions {
      flex-direction: row;
      flex-shrink: 0;
    }
  }
</style>
