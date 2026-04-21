<script lang="ts">
	import DeletePage from '$lib/components/DeletePage.svelte';
	import type { BlockedState } from '$lib/components/delete-page';
	import type { BlockingReferrer } from '$lib/delete-flow';
	import { pluralize } from '$lib/utils';
	import { submitDelete } from './credit-role-delete';

	let { data } = $props();
	let { preview, slug } = $derived(data);

	let blockedReferrers = $derived(preview.blocked_by ?? []);

	let blocked = $derived<BlockedState | null>(
		blockedReferrers.length > 0
			? {
					kind: 'referrers',
					lead: "This credit role can't be deleted because active records still credit it:",
					referrers: blockedReferrers,
					renderReferrerHref: () => null,
					renderReferrerHint: (r: BlockingReferrer) => `credits this role via ${r.relation}`,
					footer: 'Remove those credits, then try again.'
				}
			: null
	);

	let impact = $derived({
		items: ['this credit role', pluralize(preview.changeset_count, 'change set')],
		note: 'You can undo this from the toast that appears on the credit roles page, or restore the record later from its edit history.'
	});
</script>

<DeletePage
	entityLabel="Credit Role"
	entityName={preview.name}
	{slug}
	submit={submitDelete}
	cancelHref={`/credit-roles/${slug}`}
	redirectAfterDelete="/credit-roles"
	editHistoryHref={`/credit-roles/${slug}/edit-history`}
	{blocked}
	{impact}
/>
