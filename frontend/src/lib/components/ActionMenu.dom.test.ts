import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import ActionMenuFixture from './ActionMenu.fixture.svelte';

describe('ActionMenu', () => {
	function renderMenu() {
		return render(ActionMenuFixture);
	}

	it('opens on click and renders menu semantics without forcing focus into the menu', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });
		expect(trigger).toHaveAttribute('aria-expanded', 'false');
		expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
		expect(screen.queryByRole('menu')).not.toBeInTheDocument();

		await user.click(trigger);

		expect(trigger).toHaveAttribute('aria-expanded', 'true');
		expect(screen.getByRole('menu')).toBeInTheDocument();
		expect(screen.getByRole('menuitem', { name: 'Sources' })).toHaveAttribute(
			'href',
			'/models/medieval-madness/sources'
		);
		expect(trigger).toHaveFocus();
	});

	it('opens from the keyboard and focuses the first item', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });
		trigger.focus();

		await user.keyboard('{ArrowDown}');

		expect(trigger).toHaveAttribute('aria-expanded', 'true');
		expect(screen.getByRole('menu')).toBeInTheDocument();
		expect(screen.getByRole('menuitem', { name: 'Sources' })).toHaveFocus();
		expect(screen.getByRole('menuitem', { name: 'History' })).toHaveAttribute('tabindex', '-1');
	});

	it('opens from ArrowUp on the trigger and focuses the last item', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });
		trigger.focus();

		await user.keyboard('{ArrowUp}');

		expect(screen.getByRole('menuitem', { name: 'Export' })).toHaveFocus();
	});

	it('supports arrow-key roving focus and Home/End inside the menu', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });
		trigger.focus();
		await user.keyboard('{ArrowDown}');

		const sources = screen.getByRole('menuitem', { name: 'Sources' });
		const history = screen.getByRole('menuitem', { name: 'History' });
		const exportItem = screen.getByRole('menuitem', { name: 'Export' });

		expect(sources).toHaveAttribute('tabindex', '0');
		expect(history).toHaveAttribute('tabindex', '-1');

		await user.keyboard('{ArrowDown}');
		expect(history).toHaveFocus();
		expect(history).toHaveAttribute('tabindex', '0');
		expect(sources).toHaveAttribute('tabindex', '-1');

		await user.keyboard('{End}');
		expect(exportItem).toHaveFocus();

		await user.keyboard('{Home}');
		expect(sources).toHaveFocus();
	});

	it('closes on Escape and returns focus to the trigger', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });
		trigger.focus();
		await user.keyboard('{ArrowDown}');
		expect(screen.getByRole('menu')).toBeInTheDocument();

		await user.keyboard('{Escape}');

		expect(screen.queryByRole('menu')).not.toBeInTheDocument();
		expect(trigger).toHaveAttribute('aria-expanded', 'false');
		expect(trigger).toHaveFocus();
	});

	it('closes on outside pointer down', async () => {
		const user = userEvent.setup();

		renderMenu();

		const trigger = screen.getByRole('button', { name: 'Tools' });

		await user.click(trigger);
		expect(screen.getByRole('menu')).toBeInTheDocument();

		fireEvent.pointerDown(document.body);

		expect(screen.queryByRole('menu')).not.toBeInTheDocument();
		expect(trigger).toHaveAttribute('aria-expanded', 'false');
	});
});
