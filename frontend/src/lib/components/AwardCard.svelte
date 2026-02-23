<script lang="ts">
	import { resolve } from '$app/paths';
	import Card from './Card.svelte';

	let {
		slug,
		name,
		recipientCount = 0
	}: {
		slug: string;
		name: string;
		recipientCount?: number;
	} = $props();
</script>

<Card href={resolve(`/awards/${slug}`)} title={name}>
	<p class="card-count">{recipientCount} recipient{recipientCount === 1 ? '' : 's'}</p>
</Card>

<style>
	.card-count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
