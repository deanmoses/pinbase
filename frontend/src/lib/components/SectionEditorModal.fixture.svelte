<script lang="ts">
	import SectionEditorModal from './SectionEditorModal.svelte';

	let open = $state(false);
	let closeCount = $state(0);
	let saveCount = $state(0);

	function openModal() {
		open = true;
	}

	function closeModal() {
		closeCount++;
		open = false;
	}

	function saveModal() {
		saveCount++;
		open = false;
	}
</script>

<button type="button" onclick={openModal}>Open editor</button>

<SectionEditorModal heading="Overview" {open} onclose={closeModal} onsave={saveModal}>
	<label>
		Description
		<input type="text" value="Prototype content" />
	</label>
</SectionEditorModal>

<p data-testid="close-count">{closeCount}</p>
<p data-testid="save-count">{saveCount}</p>
