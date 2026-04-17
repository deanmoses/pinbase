import { getContext, setContext } from 'svelte';
import type { CombinedSectionKey } from './combined-edit-sections';
import type { ModelEditSectionKey } from './model-edit-sections';

const MODEL_KEY = Symbol('modelEditAction');
const TITLE_AREA_KEY = Symbol('titleAreaEditAction');

type ModelEditActionFn = (key: ModelEditSectionKey) => (() => void) | undefined;
type TitleAreaEditActionFn = (key: CombinedSectionKey) => (() => void) | undefined;

export function setModelEditActionContext(fn: ModelEditActionFn): void {
	setContext(MODEL_KEY, fn);
}

export function getModelEditActionContext(): ModelEditActionFn {
	const fn = getContext<ModelEditActionFn | undefined>(MODEL_KEY);
	if (!fn) {
		throw new Error('modelEditAction context missing — must be rendered inside the model layout');
	}
	return fn;
}

/**
 * Title-area context — used on the Title reader where the combined menu spans
 * both title- and model-tier sections. Keys are composite (e.g. 'title:basics',
 * 'model:overview').
 */
export function setTitleAreaEditActionContext(fn: TitleAreaEditActionFn): void {
	setContext(TITLE_AREA_KEY, fn);
}

export function getTitleAreaEditActionContext(): TitleAreaEditActionFn {
	const fn = getContext<TitleAreaEditActionFn | undefined>(TITLE_AREA_KEY);
	if (!fn) {
		throw new Error(
			'titleAreaEditAction context missing — must be rendered inside the title layout'
		);
	}
	return fn;
}

/**
 * @internal — test-only. Sets the title-area context to a no-op dispatcher so
 * SSR render tests can mount +page.svelte without also bootstrapping the
 * layout. Production code should never call this.
 */
export function setTitleAreaEditActionContextForTesting(): void {
	setContext<TitleAreaEditActionFn>(TITLE_AREA_KEY, () => undefined);
}
