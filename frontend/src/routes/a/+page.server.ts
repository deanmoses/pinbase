import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import type { PageServerLoad } from './$types';

// `/a` is an intentionally opaque prefix that will host other admin
// pages over time. While the dashboard is the only one, hitting `/a`
// itself routes there. When a second admin page lands, replace this
// redirect with a real index page.
export const load: PageServerLoad = () => {
  throw redirect(303, resolve('/a/dashboard'));
};
