<script lang="ts">
	import FieldGroup from './FieldGroup.svelte';

	let {
		label,
		value = $bindable(''),
		type = 'text',
		id = '',
		placeholder = '',
		optional = false
	}: {
		label: string;
		value?: string;
		type?: 'text' | 'url';
		id?: string;
		placeholder?: string;
		optional?: boolean;
	} = $props();
</script>

<FieldGroup {label} {id} {optional}>
	{#snippet children(inputId)}
		<input id={inputId} bind:value {type} {placeholder} />
	{/snippet}
</FieldGroup>

<style>
	input {
		width: 100%;
		padding: var(--size-2) var(--size-3);
		font-size: var(--font-size-1);
		font-family: inherit;
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
	}

	input:focus {
		outline: none;
		border-color: var(--color-input-focus);
		box-shadow: 0 0 0 3px var(--color-input-focus-ring);
	}
</style>
