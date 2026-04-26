import { describe, expect, it } from 'vitest';

import { parseApiError } from './parse-api-error';

describe('parseApiError', () => {
  it('handles structured validation error with field errors only', () => {
    const result = parseApiError({
      detail: {
        message: 'This field cannot be cleared.',
        field_errors: { name: 'This field cannot be cleared.' },
        form_errors: [],
      },
    });
    expect(result.message).toBe('name: This field cannot be cleared.');
    expect(result.fieldErrors).toEqual({ name: 'This field cannot be cleared.' });
  });

  it('handles structured validation error with form errors only', () => {
    const result = parseApiError({
      detail: {
        message: 'No changes provided.',
        field_errors: {},
        form_errors: ['No changes provided.'],
      },
    });
    expect(result.message).toBe('No changes provided.');
    expect(result.fieldErrors).toEqual({});
  });

  it('handles structured validation error with both field and form errors', () => {
    const result = parseApiError({
      detail: {
        message: 'Multiple errors.',
        field_errors: { year: 'Must be ≤ 2100.' },
        form_errors: ['Unknown slugs: [foo]'],
      },
    });
    expect(result.message).toBe('Unknown slugs: [foo] year: Must be ≤ 2100.');
    expect(result.fieldErrors).toEqual({ year: 'Must be ≤ 2100.' });
  });

  it('handles legacy string detail', () => {
    const result = parseApiError({
      detail: 'Ensure this value is less than or equal to 10.',
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
          type: 'type_error',
        },
      ],
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
