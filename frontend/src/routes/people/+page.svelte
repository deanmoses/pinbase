<script lang="ts">
	import { resolve } from '$app/paths';
	import ListPage from '$lib/components/ListPage.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();
</script>

<ListPage
	title="People"
	count={data.result.count}
	pageSize={PAGE_SIZES.people}
	entityName="person"
	entityNamePlural="people"
>
	<DataTable>
		<table>
			<thead>
				<tr>
					<th>Name</th>
					<th class="num">Credits</th>
				</tr>
			</thead>
			<tbody>
				{#each data.result.items as person (person.slug)}
					<tr>
						<td><a href={resolve(`/people/${person.slug}`)}>{person.name}</a></td>
						<td class="num">{person.credit_count}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</DataTable>
</ListPage>
