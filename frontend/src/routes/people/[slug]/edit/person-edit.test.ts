import { describe, expect, it } from 'vitest';

import { buildPersonPatchBody, personToFormFields, type PersonFormFields } from './person-edit';

const basePerson = {
	slug: 'pat-lawlor',
	name: 'Pat Lawlor',
	description: { text: 'Pinball designer.' },
	nationality: 'American',
	birth_year: 1951,
	birth_month: 10,
	birth_day: 25,
	death_year: null,
	death_month: null,
	death_day: null,
	birth_place: 'Chicago',
	photo_url: 'https://example.com/pat.jpg'
};

describe('personToFormFields', () => {
	it('maps nullable fields to editable form values', () => {
		expect(
			personToFormFields({
				...basePerson,
				description: null,
				death_year: null,
				photo_url: null
			})
		).toEqual({
			slug: 'pat-lawlor',
			name: 'Pat Lawlor',
			description: '',
			nationality: 'American',
			birth_year: 1951,
			birth_month: 10,
			birth_day: 25,
			death_year: '',
			death_month: '',
			death_day: '',
			birth_place: 'Chicago',
			photo_url: ''
		});
	});
});

describe('buildPersonPatchBody', () => {
	it('returns null when nothing changed', () => {
		expect(buildPersonPatchBody(personToFormFields(basePerson), basePerson)).toBeNull();
	});

	it('builds a scalar PATCH payload for changed fields', () => {
		const fields: PersonFormFields = {
			...personToFormFields(basePerson),
			slug: 'pat-lawlor-jr',
			nationality: 'USA',
			birth_place: 'Austin'
		};

		expect(buildPersonPatchBody(fields, basePerson)).toEqual({
			fields: {
				slug: 'pat-lawlor-jr',
				nationality: 'USA',
				birth_place: 'Austin'
			}
		});
	});

	it('maps cleared string and numeric fields to null', () => {
		const fields: PersonFormFields = {
			...personToFormFields(basePerson),
			description: '',
			birth_year: NaN,
			photo_url: ''
		};

		expect(buildPersonPatchBody(fields, basePerson)).toEqual({
			fields: {
				description: null,
				birth_year: null,
				photo_url: null
			}
		});
	});
});
