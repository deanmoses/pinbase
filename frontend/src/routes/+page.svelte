<script lang="ts">
	import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';
	import FaIcon from '$lib/components/FaIcon.svelte';
</script>

<svelte:head>
	<title>The Flip Pinball DB — Every pinball machine ever made</title>
</svelte:head>

<section class="hero">
	<h1>Every pinball machine ever made.</h1>
	<p class="subtitle">Search thousands of machines by name, manufacturer, designer, or year.</p>

	<div class="search-box">
		<FaIcon icon={faMagnifyingGlass} class="search-icon" />
		<input type="search" placeholder="Search machines..." aria-label="Search machines" />
	</div>
</section>

<style>
	.hero {
		text-align: center;
		padding: var(--size-10) 0 var(--size-8);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
		line-height: var(--font-lineheight-1);
	}

	.subtitle {
		font-size: var(--font-size-3);
		color: var(--color-text-muted);
		margin-bottom: var(--size-8);
	}

	.search-box {
		position: relative;
		max-width: 36rem;
		margin: 0 auto;
	}

	:global(.search-icon) {
		position: absolute;
		left: var(--size-4);
		top: 50%;
		transform: translateY(-50%);
		width: 1rem;
		height: 1rem;
		color: var(--color-text-muted);
		pointer-events: none;
	}

	input[type='search'] {
		width: 100%;
		padding: var(--size-3) var(--size-4) var(--size-3) var(--size-9);
		font-size: var(--font-size-2);
		font-family: var(--font-body);
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-3);
		transition:
			border-color 0.15s var(--ease-2),
			box-shadow 0.15s var(--ease-2);
	}

	input[type='search']:focus {
		outline: none;
		border-color: var(--color-input-focus);
		box-shadow: 0 0 0 3px var(--color-input-focus-ring);
	}

	input[type='search']::placeholder {
		color: var(--color-text-muted);
	}
</style>
