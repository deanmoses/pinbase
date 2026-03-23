<script lang="ts">
	import type { components } from '$lib/api/schema';
	import { resolveHref } from '$lib/utils';

	let {
		addr
	}: {
		addr: components['schemas']['AddressSchema'];
	} = $props();

	type Part = { text: string; href?: string };

	let parts = $derived.by(() => {
		const result: Part[] = [];
		if (addr.city) {
			const href =
				addr.country_slug && addr.state_slug
					? resolveHref(`/locations/${addr.country_slug}/${addr.state_slug}/${addr.city_slug}`)
					: undefined;
			result.push({ text: addr.city, href });
		}
		if (addr.state) {
			const href = addr.country_slug
				? resolveHref(`/locations/${addr.country_slug}/${addr.state_slug}`)
				: undefined;
			result.push({ text: addr.state, href });
		}
		if (addr.country) {
			result.push({
				text: addr.country,
				href: resolveHref(`/locations/${addr.country_slug}`)
			});
		}
		return result;
	});
</script>

{#if parts.length > 0}
	<span class="location">
		{#each parts as part, j (j)}
			{#if j > 0},
			{/if}
			{#if part.href}<a href={part.href}>{part.text}</a>{:else}{part.text}{/if}
		{/each}
	</span>
{/if}

<style>
	.location {
		font-style: italic;
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.location a {
		color: var(--color-accent);
		text-decoration: none;
	}

	.location a:hover {
		text-decoration: underline;
	}
</style>
