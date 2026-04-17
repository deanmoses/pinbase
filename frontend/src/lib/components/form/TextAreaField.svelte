<script lang="ts">
	import FieldGroup from './FieldGroup.svelte';

	let {
		label,
		value = $bindable(''),
		id = '',
		rows = 4,
		error = ''
	}: {
		label: string;
		value?: string;
		id?: string;
		rows?: number;
		error?: string;
	} = $props();
</script>

<FieldGroup {label} {id} {error}>
	{#snippet children(inputId, errorId)}
		<textarea
			id={inputId}
			{rows}
			bind:value
			aria-invalid={error ? true : undefined}
			aria-describedby={error ? errorId : undefined}
		></textarea>
	{/snippet}
</FieldGroup>
