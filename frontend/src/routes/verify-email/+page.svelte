<script lang="ts">
  import Page from '$lib/components/Page.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { pageTitle } from '$lib/constants';
</script>

<svelte:head>
  <title>{pageTitle('Verify your email')}</title>
</svelte:head>

<Page>
  <PageHeader title="Verify your email" />
  <p>Verify your email to start editing — please check your inbox for a confirmation link.</p>
</Page>
