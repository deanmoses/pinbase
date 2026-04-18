import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ManufacturerNameEditorFixture from './ManufacturerNameEditor.fixture.svelte';

const { PATCH } = vi.hoisted(() => ({
	PATCH: vi.fn()
}));

const { goto, invalidateAll } = vi.hoisted(() => ({
	goto: vi.fn(),
	invalidateAll: vi.fn()
}));

const { pageState } = vi.hoisted(() => ({
	pageState: {
		params: { slug: 'williams' },
		url: new URL('http://localhost:5173/manufacturers/williams?edit=name')
	}
}));

vi.mock('$lib/api/client', () => ({
	default: { PATCH }
}));

vi.mock('$app/navigation', () => ({
	goto,
	invalidateAll
}));

vi.mock('$app/state', () => ({
	page: pageState
}));

describe('ManufacturerNameEditor dirty-state contract', () => {
	beforeEach(() => {
		PATCH.mockReset();
		goto.mockReset();
		invalidateAll.mockReset();
		pageState.params.slug = 'williams';
		pageState.url = new URL('http://localhost:5173/manufacturers/williams?edit=name');
	});

	it('reports clean state initially and dirty state after editing', async () => {
		const user = userEvent.setup();
		render(ManufacturerNameEditorFixture);

		expect(screen.getByTestId('dirty-callback')).toHaveTextContent('false');

		await user.click(screen.getByRole('button', { name: 'Check dirty' }));
		expect(screen.getByTestId('dirty-handle')).toHaveTextContent('false');

		await user.clear(screen.getByLabelText('Name'));
		await user.type(screen.getByLabelText('Name'), 'Bally');

		expect(screen.getByTestId('dirty-callback')).toHaveTextContent('true');

		await user.click(screen.getByRole('button', { name: 'Check dirty' }));
		expect(screen.getByTestId('dirty-handle')).toHaveTextContent('true');
	});

	it('redirects to the renamed slug after a successful save', async () => {
		PATCH.mockResolvedValueOnce({ data: { slug: 'bally' }, error: undefined });
		invalidateAll.mockResolvedValue(undefined);

		const user = userEvent.setup();
		render(ManufacturerNameEditorFixture);

		await user.clear(screen.getByLabelText('Name'));
		await user.type(screen.getByLabelText('Name'), 'Bally');
		await user.clear(screen.getByLabelText('Slug'));
		await user.type(screen.getByLabelText('Slug'), 'bally');
		await user.click(screen.getByRole('button', { name: 'Save' }));

		expect(PATCH).toHaveBeenCalledWith('/api/manufacturers/{slug}/claims/', {
			params: { path: { slug: 'williams' } },
			body: { fields: { name: 'Bally', slug: 'bally' }, note: '' }
		});
		expect(goto).toHaveBeenCalledWith('/manufacturers/bally?edit=name', { replaceState: true });
		expect(screen.getByTestId('saved-count')).toHaveTextContent('1');
	});
});
