import client from '$lib/api/client';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ url }) => {
	const page = url.searchParams.has('page') ? Number(url.searchParams.get('page')) : undefined;

	const { data } = await client.GET('/api/people/', {
		params: { query: { page } }
	});

	if (!data) error(500, 'Failed to load people');

	return { result: data };
};
