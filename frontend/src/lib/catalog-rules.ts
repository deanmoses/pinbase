/**
 * Shared business rules derived from the data model and UX spec.
 *
 * Rules live here when they're referenced from multiple places in the
 * frontend and we want a single source of truth for the definition.
 */

/**
 * True when the given model belongs to a single-model title (i.e. the title
 * has exactly one model, which is this one). Per ModelAndTitleUX.md:143-149,
 * on such models the identity fields (name, slug, abbreviations) are
 * categorically title-owned — they cannot be edited from the model side
 * regardless of entry point, and BasicsEditor renders in slim mode.
 */
export function modelHasTitleOwnedIdentity(model: { title_models: readonly unknown[] }): boolean {
	return model.title_models.length <= 1;
}
