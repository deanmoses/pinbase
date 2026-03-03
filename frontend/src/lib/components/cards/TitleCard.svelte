<script lang="ts">
	import { resolve } from '$app/paths';
	import Card from './Card.svelte';

	let {
		slug,
		name,
		thumbnailUrl = null,
		manufacturerName = null,
		year = null
	}: {
		slug: string;
		name: string;
		thumbnailUrl?: string | null;
		manufacturerName?: string | null;
		year?: number | null;
	} = $props();

	const subtitle = $derived([manufacturerName, year].filter(Boolean).join(', ') || null);
</script>

<Card href={resolve(`/titles/${slug}`)} title={name} {thumbnailUrl}>
	{#if subtitle}
		<p class="card-subtitle">{subtitle}</p>
	{/if}
</Card>

<style>
	.card-subtitle {
		font-size: var(--font-size-1);
		color: var(--color-text-secondary);
		margin: 0;
	}
</style>
