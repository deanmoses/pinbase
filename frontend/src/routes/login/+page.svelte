<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { SITE_TITLE } from '$lib/constants';

  onMount(() => {
    const next = page.url.searchParams.get('next') || '/';
    window.location.href = `/api/auth/login/?next=${encodeURIComponent(next)}`;
  });
</script>

<svelte:head>
  <title>Redirecting to sign in — {SITE_TITLE}</title>
</svelte:head>

<div class="login-page">
  <p>Redirecting to sign in...</p>
</div>

<style>
  .login-page {
    display: flex;
    justify-content: center;
    padding: var(--size-8) 0;
    color: var(--color-text-muted);
  }
</style>
