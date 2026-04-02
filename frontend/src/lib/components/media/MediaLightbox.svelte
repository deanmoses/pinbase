<script lang="ts">
	import type { components } from '$lib/api/schema';

	type UploadedMedia = components['schemas']['UploadedMediaSchema'];

	let {
		media,
		initialIndex,
		onclose
	}: {
		media: UploadedMedia[];
		initialIndex: number;
		onclose: () => void;
	} = $props();

	// Mutable — mutated locally by prev/next. Lightbox remounts each time,
	// so capturing the initial value once is intentional.
	// svelte-ignore state_referenced_locally
	let index = $state(initialIndex);

	let item = $derived(media[index]);

	function prev() {
		if (index > 0) index--;
	}

	function next() {
		if (index < media.length - 1) index++;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
		else if (e.key === 'ArrowLeft') prev();
		else if (e.key === 'ArrowRight') next();
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) onclose();
	}

	// Lock body scroll while lightbox is open
	$effect(() => {
		const prev = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		return () => {
			document.body.style.overflow = prev;
		};
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="lightbox-backdrop" onclick={handleBackdropClick}>
	<div class="lightbox-content">
		<button class="close-btn" onclick={onclose} aria-label="Close">&times;</button>

		{#if item}
			<img src={item.renditions.display} alt="" class="display-img" />

			<div class="lightbox-footer">
				{#if item.category}
					<span class="category">{item.category}</span>
				{/if}
				<span class="counter">{index + 1} / {media.length}</span>
			</div>
		{/if}

		{#if index > 0}
			<button class="nav-btn nav-btn--prev" onclick={prev} aria-label="Previous">&#8249;</button>
		{/if}
		{#if index < media.length - 1}
			<button class="nav-btn nav-btn--next" onclick={next} aria-label="Next">&#8250;</button>
		{/if}
	</div>
</div>

<style>
	.lightbox-backdrop {
		position: fixed;
		inset: 0;
		z-index: 1000;
		background: rgba(0, 0, 0, 0.85);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.lightbox-content {
		position: relative;
		max-width: 90vw;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.display-img {
		max-width: 90vw;
		max-height: 80vh;
		object-fit: contain;
		border-radius: var(--radius-2);
	}

	.close-btn {
		position: absolute;
		top: -2.5rem;
		right: -0.5rem;
		background: none;
		border: none;
		color: #fff;
		font-size: 2rem;
		cursor: pointer;
		padding: var(--size-1);
		line-height: 1;
		opacity: 0.8;
	}

	.close-btn:hover {
		opacity: 1;
	}

	.nav-btn {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		background: rgba(0, 0, 0, 0.5);
		border: none;
		color: #fff;
		font-size: 2.5rem;
		padding: var(--size-2) var(--size-3);
		cursor: pointer;
		border-radius: var(--radius-2);
		line-height: 1;
		opacity: 0.7;
		transition: opacity 0.15s ease;
	}

	.nav-btn:hover {
		opacity: 1;
	}

	.nav-btn--prev {
		left: -4rem;
	}

	.nav-btn--next {
		right: -4rem;
	}

	.lightbox-footer {
		display: flex;
		align-items: center;
		gap: var(--size-3);
		margin-top: var(--size-2);
		color: rgba(255, 255, 255, 0.7);
		font-size: var(--font-size-1);
	}

	@media (max-width: 640px) {
		.nav-btn--prev {
			left: 0.5rem;
		}

		.nav-btn--next {
			right: 0.5rem;
		}
	}
</style>
