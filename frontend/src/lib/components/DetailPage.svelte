<script lang="ts">
	import type { Snippet } from 'svelte';
	import { pageTitle } from '$lib/constants';

	let {
		title,
		subtitle = undefined,
		children
	}: {
		title: string;
		subtitle?: Snippet;
		children: Snippet;
	} = $props();
</script>

<svelte:head>
	<title>{pageTitle(title)}</title>
</svelte:head>

<article class="detail">
	<header>
		<h1>{title}</h1>
		{#if subtitle}
			{@render subtitle()}
		{/if}
	</header>

	{@render children()}
</article>

<style>
	.detail {
		max-width: 64rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
	}

	.detail :global(h2) {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.detail :global(.empty) {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
