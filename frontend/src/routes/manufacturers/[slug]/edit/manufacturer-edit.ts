import { diffScalarFields } from '$lib/edit-helpers';

export type ManufacturerEditView = {
	slug: string;
	name: string;
	description?: { text: string } | null;
	logo_url?: string | null;
	website?: string | null;
};

export type ManufacturerFormFields = {
	slug: string;
	name: string;
	description: string;
	logo_url: string;
	website: string;
};

type ManufacturerPatchBody = {
	fields: Record<string, unknown>;
};

export function manufacturerToFormFields(
	manufacturer: ManufacturerEditView
): ManufacturerFormFields {
	return {
		slug: manufacturer.slug,
		name: manufacturer.name,
		description: manufacturer.description?.text ?? '',
		logo_url: manufacturer.logo_url ?? '',
		website: manufacturer.website ?? ''
	};
}

export function buildManufacturerPatchBody(
	fields: ManufacturerFormFields,
	manufacturer: ManufacturerEditView
): ManufacturerPatchBody | null {
	const changedFields = diffScalarFields(fields, manufacturerToFormFields(manufacturer));
	if (Object.keys(changedFields).length === 0) return null;

	return { fields: changedFields };
}
