<script lang="ts">
	import { resolve } from '$app/paths';
	import Card from './Card.svelte';

	let {
		slug,
		name,
		thumbnailUrl = null,
		short_name = null,
		machineCount = 0
	}: {
		slug: string;
		name: string;
		thumbnailUrl?: string | null;
		short_name?: string | null;
		machineCount?: number;
	} = $props();
</script>

<Card href={resolve(`/games/${slug}`)} title={name} {thumbnailUrl}>
	{#if short_name && short_name !== name}
		<p class="card-short_name">{short_name}</p>
	{/if}
	<p class="card-count">{machineCount} machine{machineCount === 1 ? '' : 's'}</p>
</Card>

<style>
	.card-short_name {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		margin-bottom: var(--size-1);
	}

	.card-count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
