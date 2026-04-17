/**
 * Combined section registry for the Title reader's edit menu.
 *
 * Single-model titles need to edit both Title- and Model-tier sections from one
 * menu and one modal host. Section-key collisions (`basics`, `external-data`)
 * are resolved with composite keys of the form `${tier}:${key}`, so a single
 * SectionEditorHost (generic over TSectionKey extends string) handles both
 * tiers without host-side changes.
 *
 * The canonical per-tier registries (MODEL_EDIT_SECTIONS, TITLE_EDIT_SECTIONS)
 * stay untouched — they're still consumed by the dedicated edit routes.
 */

import { MODEL_EDIT_SECTIONS, type ModelEditSectionDef } from './model-edit-sections';
import { titleSectionsFor, type TitleEditSectionDef } from './title-edit-sections';

export type SectionTier = 'title' | 'model';
export type CombinedSectionKey = `${SectionTier}:${string}`;

export type CombinedSectionDef = {
	key: CombinedSectionKey;
	tier: SectionTier;
	segment: string;
	/** Plain label, used as modal heading (e.g. "Basics"). */
	label: string;
	/** Label shown in the combined dropdown (disambiguated for title tier on single-model). */
	menuLabel: string;
	showCitation: boolean;
	showMixedEditWarning: boolean;
	usesSectionEditorForm: boolean;
};

function toTitleDef(s: TitleEditSectionDef, menuLabel: string): CombinedSectionDef {
	return {
		key: `title:${s.key}`,
		tier: 'title',
		segment: s.segment,
		label: s.label,
		menuLabel,
		showCitation: s.showCitation,
		showMixedEditWarning: s.showMixedEditWarning,
		// All title-tier editors use SectionEditorForm — no immediate-action title editors exist.
		usesSectionEditorForm: true
	};
}

function toModelDef(s: ModelEditSectionDef): CombinedSectionDef {
	return {
		key: `model:${s.key}`,
		tier: 'model',
		segment: s.segment,
		label: s.label,
		menuLabel: s.label,
		showCitation: s.showCitation,
		showMixedEditWarning: s.showMixedEditWarning,
		usesSectionEditorForm: s.usesSectionEditorForm
	};
}

/**
 * Single-model ordering mirrors the reader's accordion order: model Overview
 * first, then Title Details (title:basics), then the rest of the model
 * sections, with External Data - Title (title:external-data) appended last
 * next to model:external-data. Multi-model returns the natural title order.
 */
export function combinedSectionsFor(isSingleModel: boolean): CombinedSectionDef[] {
	const titleDefs = titleSectionsFor(isSingleModel);

	if (!isSingleModel) {
		// Multi-model: plain labels, no disambiguation needed.
		return titleDefs.map((s) => toTitleDef(s, s.label));
	}

	const titleByKey = new Map(titleDefs.map((s) => [s.key, s]));
	const modelOverview = MODEL_EDIT_SECTIONS.find((s) => s.key === 'overview');
	if (!modelOverview) {
		throw new Error('MODEL_EDIT_SECTIONS missing required "overview" entry');
	}
	const modelRest = MODEL_EDIT_SECTIONS.filter((s) => s.key !== 'overview');

	const out: CombinedSectionDef[] = [toModelDef(modelOverview)];
	const titleBasics = titleByKey.get('basics');
	if (titleBasics) out.push(toTitleDef(titleBasics, 'Title Details'));
	for (const s of modelRest) out.push(toModelDef(s));
	const titleExternal = titleByKey.get('external-data');
	if (titleExternal) out.push(toTitleDef(titleExternal, 'External Data - Title'));
	return out;
}
