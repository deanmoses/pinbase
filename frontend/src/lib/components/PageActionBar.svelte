<script lang="ts">
	import ActionMenu from '$lib/components/ActionMenu.svelte';

	type Props = {
		editHref: string;
		historyHref: string;
		sourcesHref: string;
	};

	let { editHref, historyHref, sourcesHref }: Props = $props();
</script>

<nav aria-label="Page actions">
	<a href={editHref}>Edit</a>
	<a href={historyHref}>History</a>
	<ActionMenu label="Tools">
		<a class="tools-item" href={sourcesHref} role="menuitem">Sources</a>
	</ActionMenu>
</nav>

<style>
	nav {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--size-4);
		padding: var(--size-2) 0 var(--size-3);
		border-bottom: 1px solid var(--color-border-soft);
		margin-bottom: var(--size-4);
	}

	nav a {
		color: var(--color-text-muted);
		text-decoration: none;
		font-size: var(--font-size-0);
	}

	nav a:hover {
		color: var(--color-accent);
	}

	.tools-item {
		display: block;
		padding: var(--size-1) var(--size-3);
		font-size: var(--font-size-0);
		outline-offset: -2px;
	}

	.tools-item:hover {
		color: var(--color-accent);
		background: var(--color-surface);
	}

	.tools-item:focus-visible {
		outline: 2px solid var(--color-accent);
	}
</style>
