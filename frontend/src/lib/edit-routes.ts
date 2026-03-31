export function getEditRedirectHref(
	resource: string,
	currentSlug: string,
	updatedSlug: string
): string | null {
	if (!updatedSlug || updatedSlug === currentSlug) return null;
	return `/${resource}/${updatedSlug}/edit`;
}
