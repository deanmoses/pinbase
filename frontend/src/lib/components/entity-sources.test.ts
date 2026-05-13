import { describe, expect, it } from 'vitest';

import { groupSourcesByField } from './entity-sources';

describe('groupSourcesByField', () => {
  it('separates conflicts, agreement, and single-source fields', () => {
    const result = groupSourcesByField([
      {
        field_name: 'year',
        value: { raw: 1997 },
        attribution: {
          source_name: 'IPDB',
          user_username: null,
          created_at: '2026-04-08T00:00:00Z',
        },
        citation: '',
        is_winner: true,
        changeset_note: null,
      },
      {
        field_name: 'year',
        value: { raw: 1998 },
        attribution: {
          source_name: 'OPDB',
          user_username: null,
          created_at: '2026-04-07T00:00:00Z',
        },
        citation: '',
        is_winner: false,
        changeset_note: null,
      },
      {
        field_name: 'description',
        value: { raw: 'Updated copy' },
        attribution: {
          source_name: null,
          user_username: 'editor',
          created_at: '2026-04-08T00:00:00Z',
        },
        citation: '',
        is_winner: true,
        changeset_note: null,
      },
      {
        field_name: 'description',
        value: { raw: 'Updated copy' },
        attribution: {
          source_name: 'IPDB',
          user_username: null,
          created_at: '2026-04-07T00:00:00Z',
        },
        citation: '',
        is_winner: false,
        changeset_note: null,
      },
      {
        field_name: 'manufacturer',
        value: { raw: 'Williams' },
        attribution: {
          source_name: 'IPDB',
          user_username: null,
          created_at: '2026-04-07T00:00:00Z',
        },
        citation: '',
        is_winner: true,
        changeset_note: null,
      },
    ]);

    expect(result.conflicts.map((group) => group.field)).toEqual(['year']);
    expect(result.agreed.map((group) => group.field)).toEqual(['description']);
    expect(result.single.map((group) => group.field)).toEqual(['manufacturer']);
  });
});
