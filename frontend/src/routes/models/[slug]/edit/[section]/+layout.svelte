<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { auth } from '$lib/auth.svelte';
	import EditSectionShell from '$lib/components/EditSectionShell.svelte';
	import type { EditSectionMenuItem } from '$lib/components/edit-section-menu';
	import { setEditLayoutContext } from '$lib/components/editors/edit-layout-context';
	import {
		MODEL_EDIT_SECTIONS,
		findSectionBySegment
	} from '$lib/components/editors/model-edit-sections';

	let { children } = $props();
	let slug = $derived(page.params.slug);
	let sectionSegment = $derived(page.params.section);
	let currentSection = $derived(sectionSegment ? findSectionBySegment(sectionSegment) : undefined);

	$effect(() => {
		auth.load();
	});

	let editorDirty = $state(false);

	setEditLayoutContext({
		setDirty(dirty: boolean) {
			editorDirty = dirty;
		}
	});

	let switcherItems: EditSectionMenuItem[] = $derived(
		MODEL_EDIT_SECTIONS.map((s) => ({
			key: s.key,
			label: s.label,
			href: resolve(`/models/${slug}/edit/${s.segment}`)
		}))
	);
</script>

<EditSectionShell
	detailHref={resolve(`/models/${slug}`)}
	{switcherItems}
	currentSectionKey={currentSection?.key}
	{editorDirty}
>
	{@render children()}
</EditSectionShell>
