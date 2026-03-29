import { diffScalarFields } from '$lib/edit-helpers';

export type PersonEditView = {
	slug: string;
	name: string;
	description?: { text: string } | null;
	nationality?: string | null;
	birth_year?: number | null;
	birth_month?: number | null;
	birth_day?: number | null;
	death_year?: number | null;
	death_month?: number | null;
	death_day?: number | null;
	birth_place?: string | null;
	photo_url?: string | null;
};

export type PersonFormFields = {
	slug: string;
	name: string;
	description: string;
	nationality: string;
	birth_year: string | number;
	birth_month: string | number;
	birth_day: string | number;
	death_year: string | number;
	death_month: string | number;
	death_day: string | number;
	birth_place: string;
	photo_url: string;
};

type PersonPatchBody = {
	fields: Record<string, unknown>;
};

export function personToFormFields(person: PersonEditView): PersonFormFields {
	return {
		slug: person.slug,
		name: person.name,
		description: person.description?.text ?? '',
		nationality: person.nationality ?? '',
		birth_year: person.birth_year ?? '',
		birth_month: person.birth_month ?? '',
		birth_day: person.birth_day ?? '',
		death_year: person.death_year ?? '',
		death_month: person.death_month ?? '',
		death_day: person.death_day ?? '',
		birth_place: person.birth_place ?? '',
		photo_url: person.photo_url ?? ''
	};
}

export function buildPersonPatchBody(
	fields: PersonFormFields,
	person: PersonEditView
): PersonPatchBody | null {
	const changedFields = diffScalarFields(fields, personToFormFields(person));
	if (Object.keys(changedFields).length === 0) return null;

	return { fields: changedFields };
}
