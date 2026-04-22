import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import TaxonomyListPage from './TaxonomyListPage.svelte';
import RowSnippetFixture from './TaxonomyListPage.row-snippet.fixture.svelte';
import HeaderSnippetFixture from './TaxonomyListPage.header-snippet.fixture.svelte';

const ITEMS = [
  { slug: 'alpha', name: 'Alpha' },
  { slug: 'beta', name: 'Beta' },
];

describe('TaxonomyListPage', () => {
  it('renders title, subtitle, and item list', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        subtitle: 'All the tags.',
        items: ITEMS,
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('Tags');
    expect(body).toContain('All the tags.');
    expect(body).toContain('Alpha');
    expect(body).toContain('Beta');
    expect(body).toContain('/tags/alpha');
    expect(body).toContain('/tags/beta');
  });

  it('renders loading state', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [],
        loading: true,
        error: null,
      },
    });

    expect(body).toContain('Loading...');
    expect(body).not.toContain('item-list');
  });

  it('renders error state', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [],
        loading: false,
        error: 'Something went wrong',
      },
    });

    expect(body).toContain('Failed to load tags.');
    expect(body).not.toContain('Alpha');
  });

  it('renders empty state', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [],
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('No tags found.');
  });

  it('applies rowStyle to row links', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: ITEMS,
        loading: false,
        error: null,
        rowStyle: 'justify-content: space-between',
      },
    });

    expect(body).toContain('justify-content: space-between');
  });

  it('includes preload link for endpoint', () => {
    const { head } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [],
        loading: false,
        error: null,
      },
    });

    expect(head).toContain('/api/tags/');
    expect(head).toContain('preload');
  });

  it('includes page title in head', () => {
    const { head } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [],
        loading: false,
        error: null,
      },
    });

    expect(head).toContain('Tags');
  });

  it('renders custom row content via rowSnippet', () => {
    const { body } = render(RowSnippetFixture);

    expect(body).toContain('Alpha');
    expect(body).toContain('42');
    expect(body).toContain('Beta');
    expect(body).not.toContain('>0<');
  });

  it('renders title_count in default row when present', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [{ slug: 'alpha', name: 'Alpha', title_count: 5 }],
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('Alpha');
    expect(body).toContain('5 titles');
  });

  it('renders title_count of 0 (does not hide zero counts)', () => {
    // Regression guard: franchises/series today render "0 titles" via custom
    // rowSnippets. Centralizing must preserve that — hiding zeros would be a
    // silent UX regression on those pages.
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'franchise',
        items: [{ slug: 'empty', name: 'Empty', title_count: 0 }],
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('Empty');
    expect(body).toContain('0 titles');
  });

  it('singularizes the count label when title_count is 1', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: [{ slug: 'lone', name: 'Lone', title_count: 1 }],
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('1 title');
    expect(body).not.toContain('1 titles');
  });

  it('omits count span when title_count is absent (e.g. credit-role shape)', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'credit-role',
        items: [{ slug: 'design', name: 'Design' }],
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('Design');
    expect(body).not.toContain('titles');
    expect(body).not.toContain('class="count"');
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
        catalogKey: 'tag',
        items: ITEMS,
        loading: false,
        error: null,
        canCreate: true,
      },
    });

    expect(body).not.toContain('type="search"');
  });

  it('renders search input at/above SEARCH_THRESHOLD', () => {
    const many = Array.from({ length: 12 }, (_, i) => ({
      slug: `t-${i}`,
      name: `Tag ${i}`,
    }));
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: many,
        loading: false,
        error: null,
        canCreate: true,
      },
    });

    expect(body).toContain('type="search"');
  });

  it('filterFn narrows the rendered list', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: ITEMS,
        loading: false,
        error: null,
        filterFn: (item: { slug: string }) => item.slug === 'alpha',
      },
    });

    expect(body).toContain('Alpha');
    expect(body).not.toContain('/tags/beta');
  });

  it('filterFn yielding zero items shows no-matches state', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: ITEMS,
        loading: false,
        error: null,
        filterFn: () => false,
      },
    });

    expect(body).toContain('No matching tags.');
    expect(body).not.toContain('/tags/alpha');
  });

  it('filterFn undefined leaves existing behavior intact', () => {
    const { body } = render(TaxonomyListPage, {
      props: {
        catalogKey: 'tag',
        items: ITEMS,
        loading: false,
        error: null,
      },
    });

    expect(body).toContain('Alpha');
    expect(body).toContain('Beta');
  });
});
