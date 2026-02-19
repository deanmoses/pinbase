<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let group = $derived(data.group);
</script>

<svelte:head>
	<title>{group.name} — The Flip Pinball DB</title>
</svelte:head>

<article>
	<header>
		<h1>{group.name}</h1>
		{#if group.shortname && group.shortname !== group.name}
			<p class="shortname">{group.shortname}</p>
		{/if}
	</header>

	{#if group.machines.length === 0}
		<p class="empty">No machines in this group.</p>
	{:else}
		<section>
			<h2>Machines ({group.machines.length})</h2>
			<div class="card-grid">
				{#each group.machines as machine (machine.slug)}
					<a href={resolve(`/models/${machine.slug}`)} class="card">
						{#if machine.thumbnail_url}
							<img src={machine.thumbnail_url} alt="" class="card-img" loading="lazy" />
						{:else}
							<div class="card-img-placeholder"></div>
						{/if}
						<div class="card-body">
							<h3 class="card-title">{machine.name}</h3>
							<div class="card-meta">
								{#if machine.manufacturer_name}
									<span>{machine.manufacturer_name}</span>
								{/if}
								{#if machine.year}
									<span>{machine.year}</span>
								{/if}
								<span>{machine.machine_type}</span>
							</div>
						</div>
					</a>
				{/each}
			</div>
		</section>
	{/if}
</article>

<style>
	article {
		max-width: 64rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.shortname {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}

	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
		gap: var(--size-4);
	}

	.card {
		display: flex;
		flex-direction: column;
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition:
			border-color 0.15s var(--ease-2),
			box-shadow 0.15s var(--ease-2);
	}

	.card:hover {
		border-color: var(--color-accent);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.card-img {
		width: 100%;
		height: 8rem;
		object-fit: cover;
	}

	.card-img-placeholder {
		width: 100%;
		height: 8rem;
		background-color: var(--color-border-soft);
	}

	.card-body {
		padding: var(--size-3);
	}

	.card-title {
		font-size: var(--font-size-2);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-1);
	}

	.card-meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--size-1);
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}

	.card-meta span:not(:last-child)::after {
		content: '·';
		margin-left: var(--size-1);
	}

	a {
		color: var(--color-link);
		text-decoration: none;
	}

	a:hover {
		text-decoration: underline;
	}
</style>
