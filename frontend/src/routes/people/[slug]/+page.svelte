<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let person = $derived(data.person);
</script>

<svelte:head>
	<title>{person.name} — The Flip Pinball DB</title>
</svelte:head>

<article>
	<header>
		<h1>{person.name}</h1>
	</header>

	{#if person.bio}
		<section class="bio">
			<p>{person.bio}</p>
		</section>
	{/if}

	{#if Object.keys(person.credits_by_role).length > 0}
		{#each Object.entries(person.credits_by_role) as [role, credits] (role)}
			<section class="role-group">
				<h2>{role}</h2>
				<ul>
					{#each credits as credit (credit.model_slug)}
						<li>
							<a href={resolve(`/models/${credit.model_slug}`)}>{credit.model_name}</a>
							<span class="role-label">{credit.role_display}</span>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{:else}
		<p class="empty">No credits listed.</p>
	{/if}
</article>

<style>
	article {
		max-width: 48rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
	}

	.bio p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
		margin-bottom: var(--size-6);
	}

	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.role-group {
		margin-bottom: var(--size-6);
	}

	ul {
		list-style: none;
		padding: 0;
	}

	li {
		display: flex;
		justify-content: space-between;
		padding: var(--size-2) 0;
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
	}

	.role-label {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}

	a {
		color: var(--color-link);
		text-decoration: none;
	}

	a:hover {
		text-decoration: underline;
	}
</style>
