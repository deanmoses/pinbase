<script lang="ts">
	import TitleExternalDataEditor from './TitleExternalDataEditor.svelte';

	type ExternalDataTitle = {
		opdb_id?: string | null;
		fandom_page_id?: number | null;
	};

	let {
		initialTitle,
		slug = 'addams-family'
	}: {
		initialTitle: ExternalDataTitle;
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
</script>

<TitleExternalDataEditor
	bind:this={editorRef}
	{initialTitle}
	{slug}
	onsaved={() => savedCount++}
	onerror={(message) => (lastError = message)}
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
