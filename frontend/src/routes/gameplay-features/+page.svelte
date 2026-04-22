<script lang="ts">
  import client from '$lib/api/client';
  import { createAsyncLoader } from '$lib/async-loader.svelte';
  import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

  const loader = createAsyncLoader(async () => {
    const { data } = await client.GET('/api/gameplay-features/');
    return data ?? [];
  }, []);
</script>

<TaxonomyListPage
  catalogKey="gameplay-feature"
  subtitle="Mechanical and digital features that define how a game plays."
  items={loader.data}
  loading={loader.loading}
  error={loader.error}
  canCreate
/>
