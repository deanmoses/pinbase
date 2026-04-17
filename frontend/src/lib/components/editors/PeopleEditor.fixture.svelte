<script lang="ts">
	import type { components } from '$lib/api/schema';
	import PeopleEditor from './PeopleEditor.svelte';

	type Credit = components['schemas']['CreditSchema'];

	let {
		initialCredits = [],
		slug = 'medieval-madness'
	}: {
		initialCredits?: Credit[];
		slug?: string;
	} = $props();

	let dirtyFromCallback = $state(false);
	let dirtyFromHandle = $state('unknown');
	let savedCount = $state(0);
	let lastError = $state('');

	let editorRef:
		| {
				save(meta?: unknown): Promise<void>;
				isDirty(): boolean;
		  }
		| undefined = $state();

	function handleSaved() {
		savedCount++;
	}

	function handleError(msg: string) {
		lastError = msg;
	}
</script>

<PeopleEditor
	bind:this={editorRef}
	{initialCredits}
	{slug}
	onsaved={handleSaved}
	onerror={handleError}
	ondirtychange={(dirty) => (dirtyFromCallback = dirty)}
/>

<button type="button" onclick={() => (dirtyFromHandle = String(editorRef?.isDirty() ?? false))}>
	Check dirty
</button>
<button type="button" onclick={() => editorRef?.save()}>Save</button>

<p data-testid="dirty-callback">{String(dirtyFromCallback)}</p>
<p data-testid="dirty-handle">{dirtyFromHandle}</p>
<p data-testid="saved-count">{savedCount}</p>
<p data-testid="last-error">{lastError}</p>
