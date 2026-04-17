import type { SaveMeta } from './save-claims-shared';

export type EditorDirtyChange = (dirty: boolean) => void;

export type SectionEditorHandle = {
	save(meta?: SaveMeta): Promise<void>;
	isDirty(): boolean;
};
