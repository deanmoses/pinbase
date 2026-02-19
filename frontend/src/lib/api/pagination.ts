/**
 * Page sizes matching the backend Django Ninja pagination config.
 * See backend/apps/machines/api.py @paginate decorators.
 */
export const PAGE_SIZES = {
	manufacturers: 50,
	people: 50
} as const;
