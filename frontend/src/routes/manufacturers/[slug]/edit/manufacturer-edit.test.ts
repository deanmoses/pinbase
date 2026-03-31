import { describe, expect, it } from 'vitest';

import {
	buildManufacturerPatchBody,
	manufacturerToFormFields,
	type ManufacturerFormFields
} from './manufacturer-edit';

const baseManufacturer = {
	slug: 'williams',
	name: 'Williams',
	description: { text: 'Chicago manufacturer.' },
	logo_url: 'https://example.com/logo.png',
	website: 'https://example.com'
};

describe('manufacturerToFormFields', () => {
	it('maps nullable values to empty strings', () => {
		expect(
			manufacturerToFormFields({
				...baseManufacturer,
				description: null,
				logo_url: null,
				website: null
			})
		).toEqual({
			slug: 'williams',
			name: 'Williams',
			description: '',
			logo_url: '',
			website: ''
		});
	});
});

describe('buildManufacturerPatchBody', () => {
	it('returns null when nothing changed', () => {
		expect(
			buildManufacturerPatchBody(manufacturerToFormFields(baseManufacturer), baseManufacturer)
		).toBeNull();
	});

	it('builds a payload for changed scalar fields', () => {
		const fields: ManufacturerFormFields = {
			...manufacturerToFormFields(baseManufacturer),
			slug: 'williams-electronics',
			name: 'Williams Electronics',
			website: 'https://williams.example'
		};

		expect(buildManufacturerPatchBody(fields, baseManufacturer)).toEqual({
			fields: {
				slug: 'williams-electronics',
				name: 'Williams Electronics',
				website: 'https://williams.example'
			}
		});
	});

	it('maps cleared fields to null', () => {
		const fields: ManufacturerFormFields = {
			...manufacturerToFormFields(baseManufacturer),
			description: '',
			logo_url: ''
		};

		expect(buildManufacturerPatchBody(fields, baseManufacturer)).toEqual({
			fields: {
				description: null,
				logo_url: null
			}
		});
	});
});
