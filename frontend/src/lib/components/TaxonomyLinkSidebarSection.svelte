<script lang="ts">
	import SidebarList from '$lib/components/SidebarList.svelte';
	import SidebarListItem from '$lib/components/SidebarListItem.svelte';
	import SidebarSection from '$lib/components/SidebarSection.svelte';
	import { resolveHref } from '$lib/utils';

	let {
		heading,
		basePath,
		item
	}: {
		heading: string;
		/** Section prefix, e.g. '/franchises' or '/series'. */
		basePath: string;
		item: { slug: string; name: string } | null | undefined;
	} = $props();
</script>

{#if item}
	<SidebarSection {heading}>
		<SidebarList>
			<SidebarListItem>
				<a href={resolveHref(`${basePath}/${item.slug}`)}>{item.name}</a>
			</SidebarListItem>
		</SidebarList>
	</SidebarSection>
{/if}
