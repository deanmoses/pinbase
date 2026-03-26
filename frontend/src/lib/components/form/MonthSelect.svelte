<script lang="ts">
	import FieldGroup from './FieldGroup.svelte';

	let {
		label,
		value = $bindable(''),
		id = ''
	}: {
		label: string;
		value?: string | number;
		id?: string;
	} = $props();

	const months = [
		'January',
		'February',
		'March',
		'April',
		'May',
		'June',
		'July',
		'August',
		'September',
		'October',
		'November',
		'December'
	];
</script>

<FieldGroup {label} {id}>
	{#snippet children(inputId)}
		<select id={inputId} bind:value>
			<option value="">—</option>
			{#each months as name, i (i)}
				<option value={i + 1}>{name}</option>
			{/each}
		</select>
	{/snippet}
</FieldGroup>

<style>
	select {
		width: 100%;
		padding: var(--size-2) var(--size-3);
		font-size: var(--font-size-1);
		font-family: inherit;
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
	}

	select:focus {
		outline: none;
		border-color: var(--color-input-focus);
		box-shadow: 0 0 0 3px var(--color-input-focus-ring);
	}
</style>
