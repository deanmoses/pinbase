<svelte:head>
	<title>Dashboard — Pinball DB</title>
</svelte:head>

<h1>Dashboard</h1>
<p class="description">
	This page is client-side rendered. Auth gating is UX-only — the backend enforces access control.
</p>

<style>
	h1 {
		font-size: var(--font-size-6);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.description {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
	}
</style>
