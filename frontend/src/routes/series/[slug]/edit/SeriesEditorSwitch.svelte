<script lang="ts">
	import type { SectionEditorHandle } from '$lib/components/editors/editor-contract';
	import type { SeriesEditSectionKey } from '$lib/components/editors/series-edit-sections';
	import SeriesDescriptionEditor from './SeriesDescriptionEditor.svelte';
	import SeriesNameEditor from './SeriesNameEditor.svelte';
	import type { SeriesEditView } from './series-edit-types';

	let {
		sectionKey,
		initialData,
		slug,
		editorRef = $bindable<SectionEditorHandle | undefined>(undefined),
		onsaved,
		onerror,
		ondirtychange
	}: {
		sectionKey: SeriesEditSectionKey;
		initialData: SeriesEditView;
		slug: string;
		editorRef?: SectionEditorHandle | undefined;
		onsaved: () => void;
		onerror: (message: string) => void;
		ondirtychange: (dirty: boolean) => void;
	} = $props();
</script>

{#if sectionKey === 'name'}
	<SeriesNameEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'description'}
	<SeriesDescriptionEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{/if}
