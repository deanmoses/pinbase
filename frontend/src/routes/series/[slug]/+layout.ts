import client from '$lib/api/client';
import { error } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const prerender = false;
export const ssr = false;

export const load: LayoutLoad = async ({ params }) => {
	const { data, response } = await client.GET('/api/series/{slug}', {
		params: { path: { slug: params.slug } }
	});

	if (!data) {
		if (response?.status === 404) error(404, 'Series not found');
		error(500, 'Failed to load series');
	}

	return { series: data };
};
