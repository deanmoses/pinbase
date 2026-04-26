<script lang="ts">
  import type { Snippet } from 'svelte';
  import TaxonomyDetailBaseLayout from '$lib/components/TaxonomyDetailBaseLayout.svelte';
  import {
    SIMPLE_TAXONOMY_EDIT_SECTIONS,
    type SimpleTaxonomyEditSectionKey,
  } from '$lib/components/editors/simple-taxonomy-edit-sections';
  import SimpleTaxonomyEditorSwitch from '$lib/components/editors/SimpleTaxonomyEditorSwitch.svelte';
  import type { SimpleTaxonomyClaimsPath } from '$lib/components/editors/save-claims-shared';
  import type { SimpleTaxonomyEditView } from '$lib/components/editors/simple-taxonomy-edit-types';

  let {
    profile,
    parentLabel,
    basePath,
    parentHref,
    claimsPath,
    deleteHref,
    createChild,
    children,
  }: {
    profile: SimpleTaxonomyEditView;
    parentLabel: string;
    basePath: string;
    parentHref?: string;
    claimsPath: SimpleTaxonomyClaimsPath;
    deleteHref?: string;
    createChild?: { href: string; label: string };
    children: Snippet;
  } = $props();

  let sections = SIMPLE_TAXONOMY_EDIT_SECTIONS.map((section) => ({
    ...section,
    usesSectionEditorForm: true,
  }));
</script>

<TaxonomyDetailBaseLayout
  {profile}
  {parentLabel}
  {basePath}
  {parentHref}
  {sections}
  {deleteHref}
  {createChild}
>
  {#snippet editor(key: SimpleTaxonomyEditSectionKey, { ref, onsaved, onerror, ondirtychange })}
    <SimpleTaxonomyEditorSwitch
      sectionKey={key}
      initialData={profile}
      slug={profile.slug}
      {claimsPath}
      bind:editorRef={ref.current}
      {onsaved}
      {onerror}
      {ondirtychange}
    />
  {/snippet}
  {@render children()}
</TaxonomyDetailBaseLayout>
