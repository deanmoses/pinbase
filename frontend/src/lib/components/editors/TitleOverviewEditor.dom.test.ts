import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import TitleOverviewEditorFixture from './TitleOverviewEditor.fixture.svelte';
import { _resetCache } from '$lib/api/link-types';

const { PATCH } = vi.hoisted(() => ({
	PATCH: vi.fn()
}));

const { invalidateAll } = vi.hoisted(() => ({
	invalidateAll: vi.fn()
}));

vi.mock('$lib/api/client', () => ({
	default: { PATCH }
}));

vi.mock('$app/navigation', () => ({
	invalidateAll
}));

describe('TitleOverviewEditor dirty-state contract', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	beforeEach(() => {
		PATCH.mockReset();
		invalidateAll.mockReset();
		_resetCache();
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: async () => []
			})
		);
	});

	it('reports clean state initially and dirty state after editing', async () => {
		const user = userEvent.setup();
		render(TitleOverviewEditorFixture);

		expect(screen.getByTestId('dirty-callback')).toHaveTextContent('false');

		await user.click(screen.getByRole('button', { name: 'Check dirty' }));
		expect(screen.getByTestId('dirty-handle')).toHaveTextContent('false');

		await user.type(screen.getByLabelText('Description'), ' updated');

		expect(screen.getByTestId('dirty-callback')).toHaveTextContent('true');

		await user.click(screen.getByRole('button', { name: 'Check dirty' }));
		expect(screen.getByTestId('dirty-handle')).toHaveTextContent('true');
	});

	it('calls PATCH on /api/titles/{slug}/claims/ when saving dirty state', async () => {
		PATCH.mockResolvedValueOnce({ data: {}, error: undefined });
		const user = userEvent.setup();
		render(TitleOverviewEditorFixture);

		await user.type(screen.getByLabelText('Description'), ' updated');
		await user.click(screen.getByRole('button', { name: 'Save' }));

		expect(PATCH).toHaveBeenCalledWith(
			'/api/titles/{slug}/claims/',
			expect.objectContaining({
				params: { path: { slug: 'addams-family' } },
				body: expect.objectContaining({
					fields: expect.objectContaining({ description: 'Original description updated' })
				})
			})
		);
		expect(screen.getByTestId('saved-count')).toHaveTextContent('1');
	});
});
