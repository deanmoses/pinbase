<script lang="ts">
	import client from '$lib/api/client';
	import CreatePage from '$lib/components/CreatePage.svelte';

	let { data } = $props();
</script>

<CreatePage
	entityLabel="Title"
	initialName={data.initialName}
	submit={(body) => client.POST('/api/titles/', { body })}
	detailHref={(slug) => `/titles/${slug}`}
	cancelHref="/titles"
/>
