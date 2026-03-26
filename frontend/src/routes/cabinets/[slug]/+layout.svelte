<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { pageTitle } from '$lib/constants';
	import { auth } from '$lib/auth.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import AttributionLine from '$lib/components/AttributionLine.svelte';
	import Markdown from '$lib/components/Markdown.svelte';
	import TabNav from '$lib/components/TabNav.svelte';
	import Tab from '$lib/components/Tab.svelte';

	let { data, children } = $props();
	let profile = $derived(data.profile);
	let slug = $derived(page.params.slug);

	$effect(() => {
		auth.load();
	});

	let isDetail = $derived(
		!page.url.pathname.endsWith('/edit') && !page.url.pathname.endsWith('/activity')
	);
	let isEdit = $derived(page.url.pathname.endsWith('/edit'));
	let isActivity = $derived(page.url.pathname.endsWith('/activity'));
</script>

<svelte:head>
	<title>{pageTitle(profile.name)}</title>
</svelte:head>

<article>
	<header>
		<Breadcrumb crumbs={[{ label: 'Cabinets', href: '/cabinets' }]} current={profile.name} />
		<h1>{profile.name}</h1>
	</header>

	{#if profile.description?.html}
		<div class="description">
			<Markdown html={profile.description.html} />
			<AttributionLine attribution={profile.description.attribution} />
		</div>
	{/if}

	<TabNav>
		<Tab active={isDetail} href={resolve(`/cabinets/${slug}`)}>Detail</Tab>
		{#if auth.isAuthenticated}
			<Tab active={isEdit} href={resolve(`/cabinets/${slug}/edit`)}>Edit</Tab>
		{/if}
		<Tab active={isActivity} href={resolve(`/cabinets/${slug}/activity`)}>Activity</Tab>
	</TabNav>

	{@render children()}
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
		margin-bottom: var(--size-4);
	}

	.description {
		margin-bottom: var(--size-6);
	}
</style>
