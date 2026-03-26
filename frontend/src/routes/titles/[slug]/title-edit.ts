export type TitleEditView = {
	slug: string;
	name: string;
	description?: { text: string } | null;
	franchise?: { slug: string; name: string } | null;
	abbreviations: string[];
	machines: Array<{
		slug: string;
		name: string;
		variants?: Array<{ slug: string; name: string }>;
	}>;
	model_detail?: { slug: string } | null;
};

export type TitleEditFormState = {
	name: string;
	description: string;
	franchiseSlug: string;
	abbreviationsText: string;
};

type TitlePatchBody = {
	fields: Record<string, unknown>;
	abbreviations: string[] | null;
	note: string;
};

function normalizeAbbreviations(values: string[]): string[] {
	const seen = new Set<string>();
	const normalized: string[] = [];

	for (const rawValue of values) {
		const value = rawValue.trim();
		if (!value || seen.has(value)) continue;
		seen.add(value);
		normalized.push(value);
	}

	return normalized;
}

export function parseAbbreviations(text: string): string[] {
	return normalizeAbbreviations(text.split(/[\n,]/));
}

export function titleToFormState(title: TitleEditView): TitleEditFormState {
	return {
		name: title.name,
		description: title.description?.text ?? '',
		franchiseSlug: title.franchise?.slug ?? '',
		abbreviationsText: title.abbreviations.join(', ')
	};
}

function buildChangedTitleFields(
	form: TitleEditFormState,
	title: TitleEditView
): Record<string, unknown> {
	const original = titleToFormState(title);
	const changed: Record<string, unknown> = {};

	if (form.name !== original.name) changed.name = form.name === '' ? null : form.name;
	if (form.description !== original.description) {
		changed.description = form.description === '' ? null : form.description;
	}
	if (form.franchiseSlug !== original.franchiseSlug) {
		changed.franchise = form.franchiseSlug === '' ? null : form.franchiseSlug;
	}

	return changed;
}

function abbreviationsChanged(form: TitleEditFormState, title: TitleEditView): boolean {
	const current = [...normalizeAbbreviations(title.abbreviations)].sort();
	const desired = [...parseAbbreviations(form.abbreviationsText)].sort();
	return JSON.stringify(current) !== JSON.stringify(desired);
}

export function buildTitlePatchBody(
	form: TitleEditFormState,
	title: TitleEditView,
	note: string
): TitlePatchBody | null {
	const fields = buildChangedTitleFields(form, title);
	const hasFields = Object.keys(fields).length > 0;
	const hasAbbreviations = abbreviationsChanged(form, title);

	if (!hasFields && !hasAbbreviations) return null;

	return {
		fields,
		abbreviations: hasAbbreviations ? parseAbbreviations(form.abbreviationsText) : null,
		note: note.trim()
	};
}

export function buildModelBoundary(title: TitleEditView): {
	modelLinks: Array<{ slug: string; name: string }>;
	singleModelActions: { editHref: string; activityHref: string } | null;
} {
	const modelLinks = title.machines.flatMap((machine) => [
		{
			slug: machine.slug,
			name: machine.name
		},
		...(machine.variants ?? []).map((variant) => ({
			slug: variant.slug,
			name: variant.name
		}))
	]);
	const singleModelSlug = title.model_detail?.slug ?? null;

	return {
		modelLinks,
		singleModelActions: singleModelSlug
			? {
					editHref: `/models/${singleModelSlug}/edit`,
					activityHref: `/models/${singleModelSlug}/activity`
				}
			: null
	};
}
