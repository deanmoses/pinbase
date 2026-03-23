<script lang="ts">
	import { page } from '$app/state';
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import { resolveHref } from '$lib/utils';
	import { pageTitle } from '$lib/constants';
	import LocationDetailPage from '$lib/components/LocationDetailPage.svelte';
	import SidebarSection from '$lib/components/SidebarSection.svelte';
	import SidebarList from '$lib/components/SidebarList.svelte';
	import SidebarListItem from '$lib/components/SidebarListItem.svelte';

	let countrySlug = $derived(page.params.countrySlug!);
	let stateSlug = $derived(page.params.stateSlug!);

	const stateData = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/locations/{country_slug}/{state_slug}', {
			params: { path: { country_slug: countrySlug, state_slug: stateSlug } }
		});
		return data ?? null;
	}, null);

	let s = $derived(stateData.data);
</script>

<svelte:head>
	<title>{pageTitle(s ? `${s.name}, ${s.country_name}` : 'State')}</title>
</svelte:head>

<LocationDetailPage
	loading={stateData.loading}
	error={!stateData.loading && (!!stateData.error || !s)}
	heading={s ? `${s.name}, ${s.country_name}` : ''}
	subtitle={`${s?.manufacturer_count ?? 0} manufacturer${s?.manufacturer_count === 1 ? '' : 's'}`}
	crumbs={[
		{ label: 'Locations', href: '/locations' },
		...(s ? [{ label: s.country_name, href: `/locations/${s.country_slug}` }] : [])
	]}
	manufacturers={s?.manufacturers ?? []}
>
	{#snippet sidebar()}
		{#if s}
			<SidebarSection heading="Country">
				<SidebarList>
					<SidebarListItem>
						<a href={resolveHref(`/locations/${s.country_slug}`)}>
							{s.country_name}
						</a>
					</SidebarListItem>
				</SidebarList>
			</SidebarSection>

			{#if s.cities.length > 0}
				<SidebarSection heading="Cities">
					<SidebarList>
						{#each s.cities as city (city.slug)}
							<SidebarListItem>
								<a href={resolveHref(`/locations/${s.country_slug}/${stateSlug}/${city.slug}`)}>
									{city.name}
								</a>
								<span class="count">{city.manufacturer_count}</span>
							</SidebarListItem>
						{/each}
					</SidebarList>
				</SidebarSection>
			{/if}
		{/if}
	{/snippet}
</LocationDetailPage>

<style>
	.count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
