<script lang="ts">
	import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';
	import { saveDisplaySubtypeClaims } from './save-display-subtype-claims';

	let { data, children } = $props();
	let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
	{profile}
	parentLabel="Display Subtypes"
	basePath="/display-subtypes"
	saveClaims={saveDisplaySubtypeClaims}
	deleteHref={`/display-subtypes/${profile.slug}/delete`}
>
	{@render children()}
</SimpleTaxonomyDetailLayout>
