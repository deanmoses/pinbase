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
	let citySlug = $derived(page.params.citySlug!);

	const cityData = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/locations/{country_slug}/cities/{city_slug}', {
			params: { path: { country_slug: countrySlug, city_slug: citySlug } }
		});
		return data ?? null;
	}, null);

	let c = $derived(cityData.data);
</script>

<svelte:head>
	<title>{pageTitle(c ? `${c.name}, ${c.country_name}` : 'City')}</title>
</svelte:head>

<LocationDetailPage
	loading={cityData.loading}
	error={!cityData.loading && (!!cityData.error || !c)}
	heading={c ? `${c.name}, ${c.country_name}` : ''}
	subtitle={`${c?.manufacturer_count ?? 0} manufacturer${c?.manufacturer_count === 1 ? '' : 's'}`}
	crumbs={[
		{ label: 'Locations', href: '/locations' },
		...(c ? [{ label: c.country_name, href: `/locations/${c.country_slug}` }] : [])
	]}
	manufacturers={c?.manufacturers ?? []}
>
	{#snippet sidebar()}
		{#if c}
			<SidebarSection heading="Country">
				<SidebarList>
					<SidebarListItem>
						<a href={resolveHref(`/locations/${c.country_slug}`)}>
							{c.country_name}
						</a>
					</SidebarListItem>
				</SidebarList>
			</SidebarSection>
		{/if}
	{/snippet}
</LocationDetailPage>
