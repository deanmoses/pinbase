<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let award = $derived(data.award);
</script>

{#if award.description}
	<section class="description">
		<p>{award.description}</p>
	</section>
{/if}

{#if award.image_urls.length > 0}
	<section class="images">
		{#each award.image_urls as url (url)}
			<img src={url} alt={award.name} />
		{/each}
	</section>
{/if}

{#if award.recipients.length > 0}
	<section>
		<h2>Recipients ({award.recipients.length})</h2>
		<table class="recipients-table">
			<thead>
				<tr>
					<th>Person</th>
					<th>Year</th>
				</tr>
			</thead>
			<tbody>
				{#each award.recipients as recipient (recipient.person_slug + ':' + recipient.year)}
					<tr>
						<td>
							<a href={resolve(`/people/${recipient.person_slug}`)}>
								{recipient.person_name}
							</a>
						</td>
						<td class="year">{recipient.year ?? 'Unknown'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</section>
{:else}
	<p class="empty">No recipients listed.</p>
{/if}

<style>
	.description p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
		margin-bottom: var(--size-6);
	}

	.images {
		display: flex;
		flex-wrap: wrap;
		gap: var(--size-3);
		margin-bottom: var(--size-6);
	}

	.images img {
		max-width: 20rem;
		max-height: 16rem;
		object-fit: contain;
		border-radius: var(--radius-3);
	}

	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.recipients-table {
		width: 100%;
		border-collapse: collapse;
	}

	.recipients-table th {
		text-align: left;
		font-size: var(--font-size-0);
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: var(--size-2) var(--size-3);
		border-bottom: 2px solid var(--color-border-soft);
	}

	.recipients-table td {
		padding: var(--size-2) var(--size-3);
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
	}

	.recipients-table a {
		color: var(--color-accent);
		text-decoration: none;
	}

	.recipients-table a:hover {
		text-decoration: underline;
	}

	.year {
		color: var(--color-text-muted);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
