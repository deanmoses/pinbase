import client from '$lib/api/client';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ url }) => {
	const search = url.searchParams.get('search') ?? undefined;
	const manufacturer = url.searchParams.get('manufacturer') ?? undefined;
	const type = url.searchParams.get('type') ?? undefined;
	const display = url.searchParams.get('display') ?? undefined;
	const year_min = url.searchParams.has('year_min')
		? Number(url.searchParams.get('year_min'))
		: undefined;
	const year_max = url.searchParams.has('year_max')
		? Number(url.searchParams.get('year_max'))
		: undefined;
	const person = url.searchParams.get('person') ?? undefined;
	const ordering = url.searchParams.get('ordering') ?? undefined;
	const page = url.searchParams.has('page') ? Number(url.searchParams.get('page')) : undefined;

	const { data } = await client.GET('/api/models/', {
		params: {
			query: { search, manufacturer, type, display, year_min, year_max, person, ordering, page }
		}
	});

	if (!data) error(500, 'Failed to load models');

	return { result: data };
};
