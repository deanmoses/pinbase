import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { flushSync } from 'svelte';
import { describe, it, expect, vi } from 'vitest';
import WikilinkAutocomplete from './WikilinkAutocomplete.svelte';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const { LINK_TYPES, SEARCH_RESULTS } = vi.hoisted(() => ({
	LINK_TYPES: [
		{ name: 'title', label: 'Title', description: 'Link to a title', flow: 'standard' as const },
		{
			name: 'manufacturer',
			label: 'Manufacturer',
			description: 'Link to a manufacturer',
			flow: 'standard' as const
		},
		{ name: 'cite', label: 'Citation', description: 'Cite a source', flow: 'custom' as const }
	],
	SEARCH_RESULTS: [
		{ ref: 'attack-from-mars', label: 'Attack from Mars' },
		{ ref: 'medieval-madness', label: 'Medieval Madness' }
	]
}));

vi.mock('$lib/api/link-types', () => ({
	fetchLinkTypes: vi.fn().mockResolvedValue(LINK_TYPES),
	searchLinkTargets: vi.fn().mockResolvedValue({ results: SEARCH_RESULTS })
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderAutocomplete() {
	const oncomplete = vi.fn();
	const oncancel = vi.fn();
	const result = render(WikilinkAutocomplete, { oncomplete, oncancel });
	return { ...result, oncomplete, oncancel };
}

/** Wait for the fetchLinkTypes promise to resolve and populate the type picker. */
async function waitForTypes() {
	await vi.waitFor(() => {
		expect(screen.getByText('Title')).toBeInTheDocument();
	});
}

/**
 * Simulate a keydown forwarded from the parent textarea.
 *
 * WikilinkAutocomplete's type-picker stage doesn't listen for keyboard events
 * on its own DOM — the parent (MarkdownTextArea) captures textarea keydowns
 * and calls the exported `handleExternalKeydown` method. We replicate that
 * pattern here by calling the method on the component instance.
 */
function sendExternalKeydown(
	component: ReturnType<typeof render>['component'],
	key: string,
	opts: KeyboardEventInit = {}
) {
	flushSync(() => {
		component.handleExternalKeydown(new KeyboardEvent('keydown', { key, ...opts }));
	});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('WikilinkAutocomplete', () => {
	// -----------------------------------------------------------------------
	// Type picker stage
	// -----------------------------------------------------------------------

	it('renders the type picker with link type options', async () => {
		renderAutocomplete();
		await waitForTypes();

		expect(screen.getByText('Insert link')).toBeInTheDocument();
		expect(screen.getByText('Title')).toBeInTheDocument();
		expect(screen.getByText('Manufacturer')).toBeInTheDocument();
		expect(screen.getByText('Citation')).toBeInTheDocument();
	});

	it('highlights items with ArrowDown/ArrowUp keyboard navigation', async () => {
		const { component } = renderAutocomplete();
		await waitForTypes();

		// First item starts highlighted
		const options = screen.getAllByRole('option');
		expect(options[0]).toHaveAttribute('aria-selected', 'true');

		// ArrowDown moves to second
		sendExternalKeydown(component, 'ArrowDown');
		expect(options[0]).toHaveAttribute('aria-selected', 'false');
		expect(options[1]).toHaveAttribute('aria-selected', 'true');

		// ArrowUp moves back to first
		sendExternalKeydown(component, 'ArrowUp');
		expect(options[0]).toHaveAttribute('aria-selected', 'true');
		expect(options[1]).toHaveAttribute('aria-selected', 'false');
	});

	it('transitions to search stage on Enter', async () => {
		const { component } = renderAutocomplete();
		await waitForTypes();

		// Select "Title" (first item, already highlighted)
		sendExternalKeydown(component, 'Enter');

		// Should now show the search stage with a search input
		await vi.waitFor(() => {
			expect(screen.getByRole('textbox', { name: /search title/i })).toBeInTheDocument();
		});
	});

	it('fires oncancel on Escape', async () => {
		const { component, oncancel } = renderAutocomplete();
		await waitForTypes();

		sendExternalKeydown(component, 'Escape');

		expect(oncancel).toHaveBeenCalledOnce();
	});

	// -----------------------------------------------------------------------
	// Search stage → result selection → oncomplete callback
	// -----------------------------------------------------------------------

	it('calls oncomplete with formatted link text when a result is selected', async () => {
		const user = userEvent.setup();
		const { component, oncomplete } = renderAutocomplete();
		await waitForTypes();

		// Navigate to search stage for "Title"
		sendExternalKeydown(component, 'Enter');
		await vi.waitFor(() => {
			expect(screen.getByRole('textbox', { name: /search title/i })).toBeInTheDocument();
		});

		// Wait for initial search results to load
		await vi.waitFor(() => {
			expect(screen.getByText(SEARCH_RESULTS[0].label)).toBeInTheDocument();
		});

		// Focus the search input, ArrowDown to first result, Enter to select
		const input = screen.getByRole('textbox', { name: /search title/i });
		await user.click(input);
		await user.keyboard('{ArrowDown}');
		await user.keyboard('{Enter}');

		expect(oncomplete).toHaveBeenCalledOnce();
		expect(oncomplete).toHaveBeenCalledWith(`[[title:${SEARCH_RESULTS[0].ref}]]`);
	});
});
