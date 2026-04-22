<script lang="ts">
  import type { Snippet } from 'svelte';
  import Breadcrumb, { type Crumb } from './Breadcrumb.svelte';

  let {
    title,
    breadcrumbs = null,
    children,
  }: {
    title: string;
    breadcrumbs?: Crumb[] | null;
    children?: Snippet;
  } = $props();
</script>

<header>
  {#if breadcrumbs}
    <Breadcrumb crumbs={breadcrumbs} current={title} />
  {/if}
  <h1>{title}</h1>
  {#if children}
    {@render children()}
  {/if}
</header>

<style>
  header {
    margin-bottom: var(--page-header-mb, var(--size-6));
  }

  h1 {
    font-size: var(--font-size-7);
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: var(--page-header-title-mb, var(--size-4));
  }
</style>
