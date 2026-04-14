<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		href = undefined,
		onclick = undefined,
		children
	}: {
		href?: string;
		onclick?: () => void;
		children: Snippet;
	} = $props();
</script>

{#if href}
	<a class="menu-item" {href} role="menuitem" tabindex="-1">
		{@render children()}
	</a>
{:else}
	<button class="menu-item" type="button" role="menuitem" tabindex="-1" {onclick}>
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
	}

	.menu-item:hover,
	.menu-item:focus-visible {
		background: var(--color-surface);
		color: var(--color-accent);
	}

	.menu-item:focus-visible {
		outline: none;
	}
</style>
