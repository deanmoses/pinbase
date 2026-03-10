<script lang="ts">
	import type { components } from '$lib/api/schema';
	import { resolveHref } from '$lib/utils';

	type ReviewLink = components['schemas']['ReviewLinkSchema'];

	let { notes, links }: { notes: string; links: ReviewLink[] } = $props();
</script>

<aside class="review-banner">
	<strong>Needs review</strong>
	<p>{notes}</p>
	{#if links.length > 0}
		<p class="review-links">
			{#each links as link, i (link.url)}
				{#if i > 0}
					·
				{/if}
				{#if link.url.startsWith('/')}
					<a href={resolveHref(link.url)}>{link.label}</a>
				{:else}
					<a href={link.url}>{link.label}</a>
				{/if}
			{/each}
		</p>
	{/if}
</aside>

<style>
	.review-banner {
		background-color: color-mix(in srgb, var(--color-warning) 12%, transparent);
		border: 1px solid var(--color-warning);
		border-radius: var(--radius-2);
		padding: var(--size-3) var(--size-4);
		margin-bottom: var(--size-5);
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
	}

	.review-banner strong {
		color: var(--color-warning);
	}

	.review-banner p {
		margin-top: var(--size-1);
	}

	.review-links a {
		color: var(--color-warning);
		text-decoration: underline;
	}
</style>
