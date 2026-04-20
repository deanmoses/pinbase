<script lang="ts">
	import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';
	import { saveTechnologyGenerationClaims } from './save-technology-generation-claims';

	let { data, children } = $props();
	let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
	{profile}
	parentLabel="Technology Generations"
	basePath="/technology-generations"
	saveClaims={saveTechnologyGenerationClaims}
	deleteHref={`/technology-generations/${profile.slug}/delete`}
	createChild={{
		href: `/technology-subgenerations/new?parent=${profile.slug}`,
		label: 'subgeneration'
	}}
>
	{@render children()}
</SimpleTaxonomyDetailLayout>
