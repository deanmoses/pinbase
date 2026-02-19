<script lang="ts">
	import { resolve } from '$app/paths';
	import Card from './Card.svelte';

	let {
		slug,
		name,
		thumbnailUrl = null,
		shortname = null,
		machineCount = 0
	}: {
		slug: string;
		name: string;
		thumbnailUrl?: string | null;
		shortname?: string | null;
		machineCount?: number;
	} = $props();
</script>

<Card href={resolve(`/groups/${slug}`)} title={name} {thumbnailUrl}>
	{#if shortname && shortname !== name}
		<p class="card-shortname">{shortname}</p>
	{/if}
	<p class="card-count">{machineCount} machine{machineCount === 1 ? '' : 's'}</p>
</Card>

<style>
	.card-shortname {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		margin-bottom: var(--size-1);
	}

	.card-count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
