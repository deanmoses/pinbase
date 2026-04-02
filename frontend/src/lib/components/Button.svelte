<script lang="ts">
	import type { Snippet } from 'svelte';
	let {
		children,
		tag = 'button',
		...rest
	}: {
		children: Snippet;
		tag?: string;
		[key: string]: unknown;
	} = $props();
</script>

<svelte:element this={tag} class="btn" {...rest}>{@render children()}</svelte:element>

<style>
	.btn {
		display: inline-block;
		padding: var(--size-2) var(--size-4);
		background: var(--color-accent);
		color: #fff;
		border: none;
		border-radius: var(--radius-2);
		font-size: var(--font-size-1);
		text-decoration: none;
		cursor: pointer;
		transition: opacity 0.15s ease;
	}

	.btn:hover:not(:disabled) {
		opacity: 0.9;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
