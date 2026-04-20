<script lang="ts">
	import client from '$lib/api/client';
	import CreatePage from '$lib/components/CreatePage.svelte';

	let { data } = $props();
	let parentSlug = $derived(data.parentSlug);
	let parentName = $derived(data.parentName);
</script>

<CreatePage
	entityLabel="Subtype"
	heading={`New subtype in ${parentName}`}
	initialName={data.initialName}
	submit={(body) =>
		client.POST('/api/display-types/{parent_slug}/subtypes/', {
			params: { path: { parent_slug: parentSlug } },
			body
		})}
	detailHref={(slug) => `/display-subtypes/${slug}`}
	cancelHref={`/display-types/${parentSlug}`}
	parentBreadcrumb={{ text: parentName, href: `/display-types/${parentSlug}` }}
/>
