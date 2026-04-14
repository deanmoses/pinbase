import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import PageActionBar from './PageActionBar.svelte';

describe('PageActionBar', () => {
	it('renders the page actions with the provided hrefs', () => {
		render(PageActionBar, {
			props: {
				editHref: '/models/medieval-madness/edit',
				historyHref: '/models/medieval-madness/history',
				sourcesHref: '/models/medieval-madness/sources'
			}
		});

		expect(screen.getByRole('navigation', { name: /page actions/i })).toBeInTheDocument();
		expect(screen.getByRole('link', { name: 'Edit' })).toHaveAttribute(
			'href',
			'/models/medieval-madness/edit'
		);
		expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute(
			'href',
			'/models/medieval-madness/history'
		);
		expect(screen.getByRole('button', { name: 'Tools' })).toBeInTheDocument();
	});
});
