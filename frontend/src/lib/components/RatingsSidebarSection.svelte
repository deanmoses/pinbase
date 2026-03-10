<script lang="ts">
	import SidebarSection from './SidebarSection.svelte';

	let {
		ipdbRating,
		pinsideRating
	}: {
		ipdbRating?: number | null;
		pinsideRating?: number | null;
	} = $props();
</script>

{#if ipdbRating || pinsideRating}
	<SidebarSection heading="Ratings">
		<div class="rating-row">
			{#if ipdbRating}
				<div class="rating-badge">
					<span class="rating-value">{ipdbRating.toFixed(1)}</span>
					<span class="rating-label">IPDB</span>
				</div>
			{/if}
			{#if pinsideRating}
				<div class="rating-badge">
					<span class="rating-value">{pinsideRating.toFixed(1)}</span>
					<span class="rating-label">Pinside</span>
				</div>
			{/if}
		</div>
	</SidebarSection>
{/if}

<style>
	.rating-row {
		display: flex;
		gap: var(--size-3);
	}

	.rating-badge {
		display: flex;
		align-items: baseline;
		gap: var(--size-1);
	}

	.rating-value {
		font-size: var(--font-size-3);
		font-weight: 700;
		color: var(--color-accent);
	}

	.rating-label {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
