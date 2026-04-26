/**
 * Parse backend API error responses into a human-readable message and
 * per-field error map. Shared across every save / delete / create flow.
 */

export type FieldErrors = Record<string, string>;

type ParsedError = { message: string; fieldErrors: FieldErrors };

/**
 * Handles two response shapes:
 * 1. Structured validation: `{ detail: { message, field_errors, form_errors } }`
 *    — produced by `StructuredValidationError` and by Ninja's malformed-body
 *    handler (see `backend/config/api.py`).
 * 2. Plain detail: `{ detail: "message" }` — produced by `HttpError(...)`
 *    raises and stock Ninja 401/404/etc.
 *
 * The 422 and 429 statuses can arrive in either envelope; dispatch is by
 * body shape, not by status code.
 */
export function parseApiError(error: unknown): ParsedError {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const { detail } = error as { detail: unknown };

    if (
      typeof detail === 'object' &&
      detail !== null &&
      'message' in detail &&
      typeof (detail as { message: unknown }).message === 'string' &&
      'field_errors' in detail
    ) {
      const d = detail as {
        message: string;
        field_errors: Record<string, string>;
        form_errors: string[];
      };
      const fieldErrors = d.field_errors ?? {};
      const formErrors = d.form_errors ?? [];

      const parts = [...formErrors, ...Object.entries(fieldErrors).map(([k, v]) => `${k}: ${v}`)];
      const message = parts.length > 0 ? parts.join(' ') : d.message;

      return { message, fieldErrors };
    }

    if (typeof detail === 'string') return { message: detail, fieldErrors: {} };
  }

  if (typeof error === 'string') return { message: error, fieldErrors: {} };
  return { message: JSON.stringify(error), fieldErrors: {} };
}
