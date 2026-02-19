/** Strip diacritics and lowercase for accent-insensitive search. */
export function normalizeText(s: string): string {
	return s
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase();
}
