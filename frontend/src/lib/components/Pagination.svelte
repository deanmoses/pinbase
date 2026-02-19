<script lang="ts">
	let {
		currentPage,
		totalPages,
		onPageChange
	}: {
		currentPage: number;
		totalPages: number;
		onPageChange: (page: number) => void;
	} = $props();
</script>

{#if totalPages > 1}
	<nav class="pagination" aria-label="Pagination">
		<button onclick={() => onPageChange(currentPage - 1)} disabled={currentPage <= 1}>
			Previous
		</button>
		<span class="page-info">Page {currentPage} of {totalPages}</span>
		<button onclick={() => onPageChange(currentPage + 1)} disabled={currentPage >= totalPages}>
			Next
		</button>
	</nav>
{/if}

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--size-4);
		padding: var(--size-5) 0;
	}

	.page-info {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	button {
		padding: var(--size-2) var(--size-4);
		font-size: var(--font-size-1);
		font-family: var(--font-body);
		background-color: var(--color-surface);
		color: var(--color-text-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-2);
		cursor: pointer;
		transition:
			background-color 0.15s var(--ease-2),
			border-color 0.15s var(--ease-2);
	}

	button:hover:not(:disabled) {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
