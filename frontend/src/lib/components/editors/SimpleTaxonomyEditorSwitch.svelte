<script lang="ts">
  import DescriptionEditor from './DescriptionEditor.svelte';
  import NameEditor from './NameEditor.svelte';
  import DisplayOrderEditor from './DisplayOrderEditor.svelte';
  import type { SectionEditorHandle } from './editor-contract';
  import {
    saveSimpleTaxonomyClaims,
    type SimpleTaxonomyClaimsPath,
    type SimpleTaxonomySectionPatchBody,
  } from './save-claims-shared';
  import type { SimpleTaxonomyEditSectionKey } from './simple-taxonomy-edit-sections';
  import type { SimpleTaxonomyEditView } from './simple-taxonomy-edit-types';

  let {
    sectionKey,
    initialData,
    slug,
    claimsPath,
    editorRef = $bindable<SectionEditorHandle | undefined>(undefined),
    onsaved,
    onerror,
    ondirtychange,
  }: {
    sectionKey: SimpleTaxonomyEditSectionKey;
    initialData: SimpleTaxonomyEditView;
    slug: string;
    claimsPath: SimpleTaxonomyClaimsPath;
    editorRef?: SectionEditorHandle | undefined;
    onsaved: () => void;
    onerror: (message: string) => void;
    ondirtychange: (dirty: boolean) => void;
  } = $props();

  const saveClaims = (s: string, body: SimpleTaxonomySectionPatchBody) =>
    saveSimpleTaxonomyClaims(claimsPath, s, body);
</script>

{#if sectionKey === 'name'}
  <NameEditor
    bind:this={editorRef}
    initialData={{ name: initialData.name, slug: initialData.slug }}
    {slug}
    save={saveClaims}
    {onsaved}
    {onerror}
    {ondirtychange}
  />
{:else if sectionKey === 'description'}
  <DescriptionEditor
    bind:this={editorRef}
    initialData={initialData.description.text}
    {slug}
    save={saveClaims}
    {onsaved}
    {onerror}
    {ondirtychange}
  />
{:else if sectionKey === 'display-order'}
  <DisplayOrderEditor
    bind:this={editorRef}
    initialData={initialData.display_order ?? null}
    {slug}
    save={saveClaims}
    {onsaved}
    {onerror}
    {ondirtychange}
  />
{/if}
