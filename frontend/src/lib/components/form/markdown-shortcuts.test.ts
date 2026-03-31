import { describe, expect, it } from 'vitest';
import {
	toggleMarker,
	wrapSelection,
	insertLink,
	pasteLink,
	indentLines,
	listEnter
} from './markdown-shortcuts';

describe('toggleMarker (bold/italic)', () => {
	it('wraps selection with marker', () => {
		const r = toggleMarker('hello world', 6, 11, '**');
		expect(r.replacement).toBe('**world**');
		expect(r.selectionStart).toBe(8);
		expect(r.selectionEnd).toBe(13);
	});

	it('unwraps when markers already present', () => {
		const r = toggleMarker('hello **world** end', 8, 13, '**');
		expect(r.replacement).toBe('world');
		expect(r.replaceStart).toBe(6);
		expect(r.replaceEnd).toBe(15);
	});

	it('inserts empty marker pair with no selection', () => {
		const r = toggleMarker('hello ', 6, 6, '*');
		expect(r.replacement).toBe('**');
		expect(r.selectionStart).toBe(7);
		expect(r.selectionEnd).toBe(7);
	});
});

describe('wrapSelection', () => {
	it('wraps with backtick', () => {
		const r = wrapSelection('hello world', 6, 11, '`');
		expect(r!.replacement).toBe('`world`');
	});

	it('returns null without selection', () => {
		expect(wrapSelection('hello', 3, 3, '`')).toBeNull();
	});

	it('returns null for unknown char', () => {
		expect(wrapSelection('hello', 0, 5, '!')).toBeNull();
	});
});

describe('insertLink', () => {
	it('wraps selection as link text', () => {
		const r = insertLink('click here end', 6, 10);
		expect(r.replacement).toBe('[here](url)');
		// "url" should be selected
		expect(r.selectionStart).toBe(13);
		expect(r.selectionEnd).toBe(16);
	});

	it('inserts empty link with no selection', () => {
		const r = insertLink('text ', 5, 5);
		expect(r.replacement).toBe('[](url)');
		expect(r.selectionStart).toBe(8);
		expect(r.selectionEnd).toBe(11);
	});
});

describe('pasteLink', () => {
	it('creates markdown link from selected text + pasted URL', () => {
		const r = pasteLink('click Google end', 6, 12, 'https://google.com');
		expect(r!.replacement).toBe('[Google](https://google.com)');
	});

	it('returns null without selection', () => {
		expect(pasteLink('text', 2, 2, 'https://example.com')).toBeNull();
	});

	it('returns null for non-URL paste', () => {
		expect(pasteLink('hello world', 0, 5, 'not a url')).toBeNull();
	});

	it('accepts http URLs', () => {
		const r = pasteLink('text', 0, 4, 'http://example.com');
		expect(r).not.toBeNull();
	});
});

describe('indentLines', () => {
	it('indents single line by 2 spaces', () => {
		const r = indentLines('hello', 0, 5, false);
		expect(r.replacement).toBe('  hello');
	});

	it('indents multiple lines', () => {
		const r = indentLines('a\nb\nc', 0, 5, false);
		expect(r.replacement).toBe('  a\n  b\n  c');
	});

	it('dedents a line', () => {
		const r = indentLines('  hello', 0, 7, true);
		expect(r.replacement).toBe('hello');
	});

	it('dedents only 1 space when less than indent', () => {
		const r = indentLines(' hello', 0, 6, true);
		expect(r.replacement).toBe('hello');
	});

	it('does nothing when dedenting unindented line', () => {
		const r = indentLines('hello', 0, 5, true);
		expect(r.replacement).toBe('hello');
	});
});

describe('listEnter', () => {
	it('continues a bullet list', () => {
		const r = listEnter('- item one', 10, 10);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n- ');
	});

	it('continues a numbered list with increment', () => {
		const r = listEnter('1. first', 8, 8);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n2. ');
	});

	it('removes empty bullet item', () => {
		const r = listEnter('- ', 2, 2);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('');
		expect(r!.replaceStart).toBe(0);
	});

	it('continues a task list with unchecked checkbox', () => {
		const r = listEnter('- [x] done task', 15, 15);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n- [ ] ');
	});

	it('returns null when not on a list line', () => {
		expect(listEnter('regular text', 12, 12)).toBeNull();
	});

	it('returns null when there is a selection', () => {
		expect(listEnter('- item', 0, 4)).toBeNull();
	});

	it('splits content at cursor', () => {
		// cursor after "- hell" → afterCursor is "o world"
		const r = listEnter('- hello world', 6, 6);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n- o world');
	});

	it('continues indented list preserving indent', () => {
		const r = listEnter('  - nested item', 15, 15);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n  - ');
	});

	it('removes empty indented list item', () => {
		const r = listEnter('  - ', 4, 4);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('  ');
	});

	it('continues with + marker', () => {
		const r = listEnter('+ item', 6, 6);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n+ ');
	});

	it('continues with * marker', () => {
		const r = listEnter('* item', 6, 6);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n* ');
	});

	it('increments multi-digit numbered list', () => {
		const r = listEnter('10. tenth item', 14, 14);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n11. ');
	});

	it('handles task list with unchecked box', () => {
		const r = listEnter('- [ ] todo item', 15, 15);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n- [ ] ');
	});

	it('removes empty task list item', () => {
		const r = listEnter('- [ ] ', 6, 6);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('');
	});

	it('handles cursor on middle line of multiline text', () => {
		// 'first line\n- list item\nthird line'
		//  0123456789 0 1234567890 1 — position 22 is end of "list item"
		const r = listEnter('first line\n- list item\nthird line', 22, 22);
		expect(r).not.toBeNull();
		expect(r!.replacement).toBe('\n- ');
	});
});
