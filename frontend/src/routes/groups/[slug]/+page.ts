import client from '$lib/api/client';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	const { data, response } = await client.GET('/api/groups/{slug}', {
		params: { path: { slug: params.slug } }
	});

	if (!data) {
		if (response?.status === 404) error(404, 'Group not found');
		error(500, 'Failed to load group');
	}

	return { group: data };
};
