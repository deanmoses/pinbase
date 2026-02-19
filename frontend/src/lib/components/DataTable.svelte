<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="data-table">
	{@render children()}
</div>

<style>
	.data-table {
		overflow-x: auto;
	}

	.data-table :global(table) {
		width: 100%;
		border-collapse: collapse;
	}

	.data-table :global(th) {
		text-align: left;
		font-size: var(--font-size-0);
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: var(--size-2) var(--size-3);
		border-bottom: 2px solid var(--color-border);
	}

	.data-table :global(td) {
		padding: var(--size-2) var(--size-3);
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
	}

	.data-table :global(.num) {
		text-align: right;
	}
</style>
