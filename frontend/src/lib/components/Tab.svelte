<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		active = false,
		href,
		onclick,
		children
	}: {
		active?: boolean;
		href?: string;
		onclick?: () => void;
		children: Snippet;
	} = $props();
</script>

{#if href}
	<a class="tab" class:active {href}>
		{@render children()}
	</a>
{:else if onclick}
	<button class="tab" class:active {onclick}>
		{@render children()}
	</button>
{:else}
	<span class="tab" class:active>
		{@render children()}
	</span>
{/if}

<style>
	.tab {
		padding: var(--size-2) var(--size-4);
		font-size: var(--font-size-1);
		font-weight: 500;
		color: var(--color-text-muted);
		text-decoration: none;
		border: none;
		background: none;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		transition:
			color 0.15s,
			border-color 0.15s;
	}

	.tab:hover {
		color: var(--color-text-primary);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}
</style>
