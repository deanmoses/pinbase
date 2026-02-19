<script>
	import '../app.css';
	import Nav from '$lib/components/Nav.svelte';

	let { children } = $props();
</script>

<Nav />

<main class="page-content">
	{@render children()}
</main>

<style>
	.page-content {
		max-width: 72rem;
		margin: 0 auto;
		padding: var(--size-6) var(--size-5);
	}
</style>
