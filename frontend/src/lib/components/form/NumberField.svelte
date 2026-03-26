<script lang="ts">
	import FieldGroup from './FieldGroup.svelte';

	let {
		label,
		value = $bindable(''),
		id = '',
		min,
		max,
		step = 1
	}: {
		label: string;
		value?: string | number;
		id?: string;
		min?: number;
		max?: number;
		step?: number;
	} = $props();
</script>

<FieldGroup {label} {id}>
	{#snippet children(inputId)}
		<input id={inputId} type="number" {min} {max} {step} bind:value />
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
