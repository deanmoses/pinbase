<script lang="ts">
	import type { Snippet } from 'svelte';

	let { heading, note, children }: { heading: string; note?: string; children: Snippet } = $props();
</script>

<section class="sidebar-section">
	<h3>{heading}</h3>
	{#if note}
		<p class="note">{note}</p>
	{/if}
	{@render children()}
</section>

<style>
	.sidebar-section {
		padding-bottom: var(--size-3);
		border-bottom: 1px solid var(--color-border-soft);
	}

	.sidebar-section h3 {
		font-size: var(--font-size-1);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-1);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.note {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		margin: 0 0 var(--size-2);
	}
</style>
