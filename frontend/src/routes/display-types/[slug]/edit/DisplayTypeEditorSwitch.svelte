<script lang="ts">
	import DescriptionEditor from '$lib/components/editors/DescriptionEditor.svelte';
	import NameEditor from '$lib/components/editors/NameEditor.svelte';
	import type { SectionEditorHandle } from '$lib/components/editors/editor-contract';
	import type { DisplayTypeEditSectionKey } from '$lib/components/editors/display-type-edit-sections';
	import DisplayTypeDisplayOrderEditor from './DisplayTypeDisplayOrderEditor.svelte';
	import { saveDisplayTypeClaims } from './save-display-type-claims';
	import type { DisplayTypeEditView } from './display-type-edit-types';

	let {
		sectionKey,
		initialData,
		slug,
		editorRef = $bindable<SectionEditorHandle | undefined>(undefined),
		onsaved,
		onerror,
		ondirtychange
	}: {
		sectionKey: DisplayTypeEditSectionKey;
		initialData: DisplayTypeEditView;
		slug: string;
		editorRef?: SectionEditorHandle | undefined;
		onsaved: () => void;
		onerror: (message: string) => void;
		ondirtychange: (dirty: boolean) => void;
	} = $props();
</script>

{#if sectionKey === 'name'}
	<NameEditor
		bind:this={editorRef}
		initialData={{ name: initialData.name, slug: initialData.slug }}
		{slug}
		save={saveDisplayTypeClaims}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'description'}
	<DescriptionEditor
		bind:this={editorRef}
		initialData={initialData.description?.text ?? ''}
		{slug}
		save={saveDisplayTypeClaims}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'display-order'}
	<DisplayTypeDisplayOrderEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{/if}
