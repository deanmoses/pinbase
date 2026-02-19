/**
 * Page sizes matching the backend Django Ninja pagination config.
 * See backend/apps/machines/api.py @paginate decorators.
 */
export const PAGE_SIZES = {
	models: 25,
	groups: 25,
	manufacturers: 50,
	people: 50
} as const;
