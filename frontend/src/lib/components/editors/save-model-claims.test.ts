import { describe, expect, it, vi, beforeEach } from 'vitest';

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

import { saveModelClaims, parseApiError } from './save-model-claims';

describe('parseApiError', () => {
	it('handles structured validation error with field errors only', () => {
		const result = parseApiError({
			detail: {
				message: 'This field cannot be cleared.',
				field_errors: { name: 'This field cannot be cleared.' },
				form_errors: []
			}
		});
		expect(result.message).toBe('name: This field cannot be cleared.');
		expect(result.fieldErrors).toEqual({ name: 'This field cannot be cleared.' });
	});

	it('handles structured validation error with form errors only', () => {
		const result = parseApiError({
			detail: {
				message: 'No changes provided.',
				field_errors: {},
				form_errors: ['No changes provided.']
			}
		});
		expect(result.message).toBe('No changes provided.');
		expect(result.fieldErrors).toEqual({});
	});

	it('handles structured validation error with both field and form errors', () => {
		const result = parseApiError({
			detail: {
				message: 'Multiple errors.',
				field_errors: { year: 'Must be ≤ 2100.' },
				form_errors: ['Unknown slugs: [foo]']
			}
		});
		expect(result.message).toBe('Unknown slugs: [foo] year: Must be ≤ 2100.');
		expect(result.fieldErrors).toEqual({ year: 'Must be ≤ 2100.' });
	});

	it('handles legacy string detail', () => {
		const result = parseApiError({
			detail: 'Ensure this value is less than or equal to 10.'
		});
		expect(result.message).toBe('Ensure this value is less than or equal to 10.');
		expect(result.fieldErrors).toEqual({});
	});

	it('handles Pydantic validation array', () => {
		const result = parseApiError({
			detail: [
				{
					loc: ['body', 'fields', 'year'],
					msg: 'value is not a valid integer',
					type: 'type_error'
				}
			]
		});
		expect(result.message).toBe('year: value is not a valid integer');
		expect(result.fieldErrors).toEqual({ year: 'value is not a valid integer' });
	});

	it('handles plain string error', () => {
		const result = parseApiError('Something went wrong');
		expect(result.message).toBe('Something went wrong');
		expect(result.fieldErrors).toEqual({});
	});

	it('falls back to JSON for unknown shapes', () => {
		const result = parseApiError({ unexpected: 'shape' });
		expect(result.message).toBe('{"unexpected":"shape"}');
		expect(result.fieldErrors).toEqual({});
	});
});

describe('saveModelClaims', () => {
	beforeEach(() => {
		PATCH.mockReset();
		invalidateAll.mockReset();
	});

	it('returns ok and invalidates on success', async () => {
		PATCH.mockResolvedValue({ data: {}, error: undefined });
		invalidateAll.mockResolvedValue(undefined);

		const result = await saveModelClaims('medieval-madness', {
			fields: { description: 'new text' }
		});

		expect(result).toEqual({ ok: true });
		expect(PATCH).toHaveBeenCalledWith('/api/models/{slug}/claims/', {
			params: { path: { slug: 'medieval-madness' } },
			body: { fields: { description: 'new text' }, note: '' }
		});
		expect(invalidateAll).toHaveBeenCalledOnce();
	});

	it('extracts detail string from legacy error', async () => {
		PATCH.mockResolvedValue({
			data: undefined,
			error: { detail: 'Ensure this value is less than or equal to 10.' }
		});

		const result = await saveModelClaims('medieval-madness', {
			fields: { pinside_rating: 10234 }
		});

		expect(result).toEqual({
			ok: false,
			error: 'Ensure this value is less than or equal to 10.',
			fieldErrors: {}
		});
		expect(invalidateAll).not.toHaveBeenCalled();
	});

	it('parses structured field errors from response', async () => {
		PATCH.mockResolvedValue({
			data: undefined,
			error: {
				detail: {
					message: 'This value must be unique.',
					field_errors: { slug: 'This value must be unique.' },
					form_errors: []
				}
			}
		});

		const result = await saveModelClaims('medieval-madness', {
			fields: { slug: 'other-game' }
		});

		expect(result).toEqual({
			ok: false,
			error: 'slug: This value must be unique.',
			fieldErrors: { slug: 'This value must be unique.' }
		});
	});

	it('joins array-of-objects detail into a readable message', async () => {
		PATCH.mockResolvedValue({
			data: undefined,
			error: {
				detail: [
					{
						loc: ['body', 'fields', 'year'],
						msg: 'value is not a valid integer',
						type: 'type_error'
					}
				]
			}
		});

		const result = await saveModelClaims('medieval-madness', {
			fields: { year: 'not-a-number' }
		});

		expect(result).toEqual({
			ok: false,
			error: 'year: value is not a valid integer',
			fieldErrors: { year: 'value is not a valid integer' }
		});
	});

	it('handles string errors', async () => {
		PATCH.mockResolvedValue({ data: undefined, error: 'Something went wrong' });

		const result = await saveModelClaims('medieval-madness', {
			fields: { description: 'x' }
		});

		expect(result).toEqual({ ok: false, error: 'Something went wrong', fieldErrors: {} });
	});

	it('falls back to JSON for unknown error shapes', async () => {
		PATCH.mockResolvedValue({ data: undefined, error: { unexpected: 'shape' } });

		const result = await saveModelClaims('medieval-madness', {
			fields: { description: 'x' }
		});

		expect(result).toEqual({ ok: false, error: '{"unexpected":"shape"}', fieldErrors: {} });
	});

	it('sends credits-only body with default fields', async () => {
		PATCH.mockResolvedValue({ data: {}, error: undefined });
		invalidateAll.mockResolvedValue(undefined);

		const credits = [{ person_slug: 'pat-lawlor', role: 'game-design' }];
		await saveModelClaims('medieval-madness', { credits });

		expect(PATCH).toHaveBeenCalledWith('/api/models/{slug}/claims/', {
			params: { path: { slug: 'medieval-madness' } },
			body: { fields: {}, note: '', credits }
		});
	});

	it('passes note override', async () => {
		PATCH.mockResolvedValue({ data: {}, error: undefined });
		invalidateAll.mockResolvedValue(undefined);

		await saveModelClaims('medieval-madness', {
			fields: { year: 1997 },
			note: 'Corrected per IPDB'
		});

		expect(PATCH).toHaveBeenCalledWith('/api/models/{slug}/claims/', {
			params: { path: { slug: 'medieval-madness' } },
			body: { fields: { year: 1997 }, note: 'Corrected per IPDB' }
		});
	});

	it('passes citation override', async () => {
		PATCH.mockResolvedValue({ data: {}, error: undefined });
		invalidateAll.mockResolvedValue(undefined);

		const citation = { citation_instance_id: 42 };
		await saveModelClaims('medieval-madness', {
			fields: { year: 1997 },
			citation
		});

		expect(PATCH).toHaveBeenCalledWith('/api/models/{slug}/claims/', {
			params: { path: { slug: 'medieval-madness' } },
			body: { fields: { year: 1997 }, note: '', citation }
		});
	});
});
