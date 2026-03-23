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

	const country = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/locations/{country_slug}', {
			params: { path: { country_slug: countrySlug } }
		});
		return data ?? null;
	}, null);

	type FlatCity = {
		name: string;
		slug: string;
		manufacturer_count: number;
		stateName: string | null;
		stateSlug: string | null;
		href: string;
	};

	let allCities = $derived.by((): FlatCity[] => {
		const d = country.data;
		if (!d) return [];
		const cities: FlatCity[] = [];
		for (const city of d.cities) {
			cities.push({
				...city,
				stateName: null,
				stateSlug: null,
				href: `/locations/${countrySlug}/cities/${city.slug}`
			});
		}
		for (const state of d.states) {
			for (const city of state.cities) {
				cities.push({
					...city,
					stateName: state.name,
					stateSlug: state.slug,
					href: `/locations/${countrySlug}/${state.slug}/${city.slug}`
				});
			}
		}
		cities.sort(
			(a, b) => b.manufacturer_count - a.manufacturer_count || a.name.localeCompare(b.name)
		);
		return cities;
	});

	let sortedStates = $derived.by(() => {
		const d = country.data;
		if (!d) return [];
		return [...d.states].sort(
			(a, b) => b.manufacturer_count - a.manufacturer_count || a.name.localeCompare(b.name)
		);
	});
</script>

<svelte:head>
	<title>{pageTitle(country.data?.name ?? 'Country')}</title>
</svelte:head>

<LocationDetailPage
	loading={country.loading}
	error={!country.loading && (!!country.error || !country.data)}
	heading={country.data?.name ?? ''}
	subtitle={`${country.data?.manufacturer_count ?? 0} manufacturer${country.data?.manufacturer_count === 1 ? '' : 's'}`}
	crumbs={[{ label: 'Locations', href: '/locations' }]}
	manufacturers={country.data?.manufacturers ?? []}
>
	{#snippet sidebar()}
		{#if sortedStates.length > 0}
			<SidebarSection heading="States">
				<SidebarList>
					{#each sortedStates as state (state.slug)}
						<SidebarListItem>
							<a href={resolveHref(`/locations/${countrySlug}/${state.slug}`)}>
								{state.name}
							</a>
							<span class="count">{state.manufacturer_count}</span>
						</SidebarListItem>
					{/each}
				</SidebarList>
			</SidebarSection>
		{/if}

		{#if allCities.length > 0}
			<SidebarSection heading="Cities">
				<SidebarList>
					{#each allCities as city (city.href)}
						<SidebarListItem>
							<span class="city-entry">
								<a href={resolveHref(city.href)}>{city.name}</a
								>{#if city.stateName && city.stateSlug}, <a
										href={resolveHref(`/locations/${countrySlug}/${city.stateSlug}`)}
										class="state-link">{city.stateName}</a
									>{/if}
							</span>
							<span class="count">{city.manufacturer_count}</span>
						</SidebarListItem>
					{/each}
				</SidebarList>
			</SidebarSection>
		{/if}
	{/snippet}
</LocationDetailPage>

<style>
	.count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}

	.state-link {
		color: var(--color-text-muted);
		text-decoration: none;
	}

	.state-link:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
</style>
