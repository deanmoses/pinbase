<script lang="ts">
  import AccordionSection from '$lib/components/AccordionSection.svelte';
  import ManufacturerCardGrid from '$lib/components/ManufacturerCardGrid.svelte';
  import RichTextOverviewAccordion from '$lib/components/RichTextOverviewAccordion.svelte';
  import RichTextReferencesAccordion from '$lib/components/RichTextReferencesAccordion.svelte';
  import { createRichTextAccordionState } from '$lib/components/rich-text-accordion-state.svelte';
  import { locationEditActionContext } from '$lib/components/editors/edit-action-context';
  import type { LocationDetailSchema } from '$lib/api/schema';

  type LocationDetail = LocationDetailSchema;

  let { data } = $props();
  let profile = $derived<LocationDetail>(data.profile);
  let editAction = locationEditActionContext.get();
  const richTextState = createRichTextAccordionState();
  let manufacturersHeading = $derived(`Manufacturers (${profile.manufacturer_count})`);
</script>

{#if profile.description?.html}
  <RichTextOverviewAccordion
    richText={profile.description}
    state={richTextState}
    onEdit={editAction('description')}
  />
{/if}

<AccordionSection heading={manufacturersHeading} open={true}>
  <ManufacturerCardGrid manufacturers={profile.manufacturers} showCount={false} />
</AccordionSection>

<RichTextReferencesAccordion richText={profile.description} state={richTextState} />
