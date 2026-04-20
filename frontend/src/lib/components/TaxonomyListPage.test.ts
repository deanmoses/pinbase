import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import TaxonomyListPage from './TaxonomyListPage.svelte';
import RowSnippetFixture from './TaxonomyListPage.row-snippet.fixture.svelte';
import HeaderSnippetFixture from './TaxonomyListPage.header-snippet.fixture.svelte';

const ITEMS = [
	{ slug: 'alpha', name: 'Alpha' },
	{ slug: 'beta', name: 'Beta' }
];

describe('TaxonomyListPage', () => {
	it('renders title, subtitle, and item list', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				subtitle: 'All the widgets.',
				basePath: '/widgets',
				items: ITEMS,
				loading: false,
				error: null
			}
		});

		expect(body).toContain('Widgets');
		expect(body).toContain('All the widgets.');
		expect(body).toContain('Alpha');
		expect(body).toContain('Beta');
		expect(body).toContain('/widgets/alpha');
		expect(body).toContain('/widgets/beta');
	});

	it('renders loading state', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: [],
				loading: true,
				error: null
			}
		});

		expect(body).toContain('Loading...');
		expect(body).not.toContain('item-list');
	});

	it('renders error state', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: [],
				loading: false,
				error: 'Something went wrong'
			}
		});

		expect(body).toContain('Failed to load widgets.');
		expect(body).not.toContain('Alpha');
	});

	it('renders empty state', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: [],
				loading: false,
				error: null
			}
		});

		expect(body).toContain('No widgets found.');
	});

	it('applies rowStyle to row links', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: ITEMS,
				loading: false,
				error: null,
				rowStyle: 'justify-content: space-between'
			}
		});

		expect(body).toContain('justify-content: space-between');
	});

	it('includes preload link for endpoint', () => {
		const { head } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: [],
				loading: false,
				error: null
			}
		});

		expect(head).toContain('/api/widgets/');
		expect(head).toContain('preload');
	});

	it('includes page title in head', () => {
		const { head } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: [],
				loading: false,
				error: null
			}
		});

		expect(head).toContain('Widgets');
	});

	it('renders custom row content via rowSnippet', () => {
		const { body } = render(RowSnippetFixture);

		expect(body).toContain('Alpha');
		expect(body).toContain('42');
		expect(body).toContain('Beta');
		expect(body).not.toContain('>0<');
	});

	it('renders custom header content via headerSnippet', () => {
		const { body } = render(HeaderSnippetFixture);

		expect(body).toContain('Rich introductory content here.');
		expect(body).not.toContain('subtitle');
	});

	it('omits search input below SEARCH_THRESHOLD', () => {
		// 2 items is far below the 12-item threshold.
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: ITEMS,
				loading: false,
				error: null,
				createHref: '/widgets/new'
			}
		});

		expect(body).not.toContain('type="search"');
	});

	it('renders search input at/above SEARCH_THRESHOLD', () => {
		const many = Array.from({ length: 12 }, (_, i) => ({
			slug: `w-${i}`,
			name: `Widget ${i}`
		}));
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: many,
				loading: false,
				error: null,
				createHref: '/widgets/new'
			}
		});

		expect(body).toContain('type="search"');
	});

	it('does not render create affordances when createHref is absent', () => {
		const { body } = render(TaxonomyListPage, {
			props: {
				title: 'Widgets',
				basePath: '/widgets',
				items: ITEMS,
				loading: false,
				error: null
			}
		});

		expect(body).not.toContain('/widgets/new');
	});
});
