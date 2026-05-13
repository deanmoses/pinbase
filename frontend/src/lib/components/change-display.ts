import type { FieldChangeSchema } from '$lib/api/schema';

type FieldChange = FieldChangeSchema;

/**
 * Type guard: true when both old and new values are strings and at least one
 * exceeds 80 characters, meaning the change should render as an InlineDiff
 * rather than a simple old → new display.
 */
export function isDiffable(
  change: FieldChange,
): change is FieldChange & { old_value: string; new_value: string } {
  return (
    typeof change.old_value === 'string' &&
    typeof change.new_value === 'string' &&
    (change.old_value.length > 80 || change.new_value.length > 80)
  );
}

/**
 * True when a change asserts the same value that already existed — e.g. a
 * second ingest source confirming the canonical value. Such rows should
 * render as a single value, not as an old → new transition.
 */
export function isUnchanged(change: FieldChange): boolean {
  const { old_value, new_value } = change;
  if (old_value === new_value) return true;
  if (old_value == null || new_value == null) return false;
  return JSON.stringify(old_value) === JSON.stringify(new_value);
}

/**
 * If `v` is a simple relationship-claim dict — `{exists: bool, <key>: string}`
 * with exactly one non-`exists` key and a string value — return the scalar
 * along with the existence flag, so the caller can render `DW` (or struck-
 * through `DW` when `exists` is false) instead of the raw JSON dict.
 *
 * Returns null for shapes that need richer rendering (credits, gameplay
 * features, media attachments, FK-pk relationships, alias_value+display).
 * Bare scalars also return null — those go straight through `formatValue`.
 */
export function simplifyClaimValue(v: unknown): { display: string; exists: boolean } | null {
  if (v === null || typeof v !== 'object' || Array.isArray(v)) return null;
  const obj = v as Record<string, unknown>;
  if (typeof obj.exists !== 'boolean') return null;
  const otherKeys = Object.keys(obj).filter((k) => k !== 'exists');
  if (otherKeys.length !== 1) return null;
  const scalar = obj[otherKeys[0]];
  if (typeof scalar !== 'string') return null;
  return { display: scalar, exists: obj.exists };
}

/** Format an unknown claim value for inline display, with truncation. */
export function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '\u2014';
  const s = typeof v === 'string' ? v : JSON.stringify(v);
  return s.length > 120 ? s.slice(0, 120) + '...' : s;
}
