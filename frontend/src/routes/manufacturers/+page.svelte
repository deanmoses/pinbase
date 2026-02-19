<script lang="ts">
	import { resolve } from '$app/paths';
	import ListPage from '$lib/components/ListPage.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();
</script>

<ListPage
	title="Manufacturers"
	count={data.result.count}
	pageSize={PAGE_SIZES.manufacturers}
	entityName="manufacturer"
>
	<DataTable>
		<table>
			<thead>
				<tr>
					<th>Name</th>
					<th>Trade Name</th>
					<th class="num">Models</th>
				</tr>
			</thead>
			<tbody>
				{#each data.result.items as mfr (mfr.slug)}
					<tr>
						<td><a href={resolve(`/manufacturers/${mfr.slug}`)}>{mfr.name}</a></td>
						<td>{mfr.trade_name || '—'}</td>
						<td class="num">{mfr.model_count}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</DataTable>
</ListPage>
