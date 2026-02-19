<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';
	import FaIcon from './FaIcon.svelte';

	let {
		placeholder,
		ariaLabel
	}: {
		placeholder: string;
		ariaLabel: string;
	} = $props();

	let searchValue = $state(page.url.searchParams.get('search') ?? '');

	function handleSearch(e: SubmitEvent) {
		e.preventDefault();
		const url = new URL(page.url);
		if (searchValue.trim()) {
			url.searchParams.set('search', searchValue.trim());
		} else {
			url.searchParams.delete('search');
		}
		url.searchParams.delete('page');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same-page param update
		goto(url, { keepFocus: true });
	}
</script>

<form class="search-bar" onsubmit={handleSearch}>
	<div class="search-box">
		<FaIcon icon={faMagnifyingGlass} class="search-icon" />
		<input type="search" {placeholder} aria-label={ariaLabel} bind:value={searchValue} />
	</div>
</form>

<style>
	.search-bar {
		margin-bottom: var(--size-5);
	}

	.search-box {
		position: relative;
		max-width: 24rem;
	}

	:global(.search-box .search-icon) {
		position: absolute;
		left: var(--size-3);
		top: 50%;
		transform: translateY(-50%);
		width: 0.875rem;
		height: 0.875rem;
		color: var(--color-text-muted);
		pointer-events: none;
	}

	input[type='search'] {
		width: 100%;
		padding: var(--size-2) var(--size-3) var(--size-2) var(--size-8);
		font-size: var(--font-size-1);
		font-family: var(--font-body);
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
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
