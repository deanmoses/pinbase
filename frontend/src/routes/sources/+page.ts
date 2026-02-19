import client from '$lib/api/client';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = async () => {
	const { data } = await client.GET('/api/sources/');

	if (!data) error(500, 'Failed to load sources');

	return { sources: data };
};
