<script lang="ts">
	import DetailPage from '$lib/components/DetailPage.svelte';
	import CardGrid from '$lib/components/CardGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';

	let { data } = $props();
	let person = $derived(data.person);
</script>

<DetailPage title={person.name}>
	{#if person.bio}
		<section class="bio">
			<p>{person.bio}</p>
		</section>
	{/if}

	{#if Object.keys(person.credits_by_role).length > 0}
		{#each Object.entries(person.credits_by_role) as [role, credits] (role)}
			<section class="role-group">
				<h2>{role} ({credits.length})</h2>
				<CardGrid>
					{#each credits as credit (credit.model_slug)}
						<MachineCard
							slug={credit.model_slug}
							name={credit.model_name}
							thumbnailUrl={credit.thumbnail_url}
						/>
					{/each}
				</CardGrid>
			</section>
		{/each}
	{:else}
		<p class="empty">No credits listed.</p>
	{/if}
</DetailPage>

<style>
	.bio p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
		margin-bottom: var(--size-6);
	}

	.role-group {
		margin-bottom: var(--size-6);
	}
</style>
