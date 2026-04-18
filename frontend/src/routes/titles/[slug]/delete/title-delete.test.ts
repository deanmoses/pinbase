import { beforeEach, describe, expect, it, vi } from 'vitest';

const POST = vi.fn();

vi.mock('$lib/api/client', () => ({
	default: { POST }
}));

vi.mock('$lib/edit-citation', () => ({
	buildEditCitationRequest: () => null
}));

// Import after mocks so the module closes over the mocked client.
const { submitDelete, submitUndoDelete } = await import('./title-delete');

function makeResponse(status: number, headers: Record<string, string> = {}): Response {
	return new Response(null, { status, headers });
}

beforeEach(() => {
	POST.mockReset();
});

describe('submitDelete', () => {
	it('returns ok with the delete response on 200', async () => {
		POST.mockResolvedValue({
			data: { changeset_id: 42, affected_titles: ['g'], affected_models: [] },
			error: undefined,
			response: makeResponse(200)
		});
		const out = await submitDelete('g');
		expect(out.kind).toBe('ok');
		if (out.kind === 'ok') {
			expect(out.data.changeset_id).toBe(42);
		}
	});

	it('classifies 429 as rate_limited and surfaces Retry-After hours', async () => {
		POST.mockResolvedValue({
			data: undefined,
			error: undefined,
			response: makeResponse(429, { 'Retry-After': '86400' })
		});
		const out = await submitDelete('g');
		expect(out.kind).toBe('rate_limited');
		if (out.kind === 'rate_limited') {
			expect(out.retryAfterSeconds).toBe(86400);
			expect(out.message).toMatch(/\d+ hour/);
		}
	});

	it('classifies 422 with blocked_by as a blocked outcome', async () => {
		const blockedBody = {
			detail: 'Cannot delete: active references.',
			blocked_by: [
				{
					entity_type: 'machinemodel',
					slug: 'other',
					name: 'Other',
					relation: 'variant_of',
					blocked_target_type: 'machinemodel',
					blocked_target_slug: 'target-pro'
				}
			]
		};
		POST.mockResolvedValue({
			data: undefined,
			error: blockedBody,
			response: new Response(JSON.stringify(blockedBody), {
				status: 422,
				headers: { 'content-type': 'application/json' }
			})
		});
		const out = await submitDelete('target');
		expect(out.kind).toBe('blocked');
		if (out.kind === 'blocked') {
			expect(out.blockedBy).toHaveLength(1);
			expect(out.blockedBy[0].slug).toBe('other');
		}
	});

	it('falls back to form_error for unexpected failures', async () => {
		POST.mockResolvedValue({
			data: undefined,
			error: { detail: 'server blew up' },
			response: makeResponse(500)
		});
		const out = await submitDelete('g');
		expect(out.kind).toBe('form_error');
		if (out.kind === 'form_error') {
			expect(out.message).toContain('server blew up');
		}
	});
});

describe('submitUndoDelete', () => {
	it('returns ok with the revert changeset id', async () => {
		POST.mockResolvedValue({
			data: { ok: true, changeset_id: 99 },
			error: undefined,
			response: makeResponse(200)
		});
		const out = await submitUndoDelete(42);
		expect(out.kind).toBe('ok');
		if (out.kind === 'ok') expect(out.changesetId).toBe(99);
	});

	it('maps 422 to superseded (the common not-latest-action case)', async () => {
		POST.mockResolvedValue({
			data: undefined,
			error: { detail: 'not latest' },
			response: makeResponse(422)
		});
		const out = await submitUndoDelete(42);
		expect(out.kind).toBe('superseded');
	});
});
