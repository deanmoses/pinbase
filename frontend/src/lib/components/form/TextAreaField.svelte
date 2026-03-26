<script lang="ts">
	import FieldGroup from './FieldGroup.svelte';

	let {
		label,
		value = $bindable(''),
		id = '',
		rows = 4
	}: {
		label: string;
		value?: string;
		id?: string;
		rows?: number;
	} = $props();
</script>

<FieldGroup {label} {id}>
	{#snippet children(inputId)}
		<textarea id={inputId} {rows} bind:value></textarea>
	{/snippet}
</FieldGroup>

<style>
	textarea {
		width: 100%;
		padding: var(--size-2) var(--size-3);
		font-size: var(--font-size-1);
		font-family: inherit;
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
		resize: vertical;
	}

	textarea:focus {
		outline: none;
		border-color: var(--color-input-focus);
		box-shadow: 0 0 0 3px var(--color-input-focus-ring);
	}
</style>
