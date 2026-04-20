<script lang="ts">
	import DeletePage from '$lib/components/DeletePage.svelte';
	import type { BlockedState } from '$lib/components/delete-page';
	import type { BlockingReferrer } from '$lib/delete-flow';
	import { pluralize } from '$lib/utils';
	import { submitDelete } from './tag-delete';

	let { data } = $props();
	let { preview, slug } = $derived(data);

	let blockedReferrers = $derived(preview.blocked_by ?? []);

	let blocked = $derived<BlockedState | null>(
		blockedReferrers.length > 0
			? {
					kind: 'referrers',
					lead: "This tag can't be deleted because active records still point at it:",
					referrers: blockedReferrers,
					renderReferrerHref: () => null,
					renderReferrerHint: (r: BlockingReferrer) => `references this tag via ${r.relation}`,
					footer: 'Resolve these references, then try again.'
				}
			: null
	);

	let impact = $derived({
		items: ['this tag', pluralize(preview.changeset_count, 'change set')],
		note: 'You can undo this from the toast that appears on the tags page, or restore the record later from its edit history.'
	});
</script>

<DeletePage
	entityLabel="Tag"
	entityName={preview.name}
	{slug}
	submit={submitDelete}
	cancelHref={`/tags/${slug}`}
	redirectAfterDelete="/tags"
	editHistoryHref={`/tags/${slug}/edit-history`}
	{blocked}
	{impact}
/>
