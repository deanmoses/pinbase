<script lang="ts">
  import type { ChangeSetAttributionSchema } from '$lib/api/schema';
  import UserLink from './UserLink.svelte';

  let { attribution }: { attribution: ChangeSetAttributionSchema } = $props();
</script>

{#if attribution.is_ingest}
  {attribution.source_name ?? 'system'}
{:else if attribution.user_username}
  <UserLink username={attribution.user_username} />
{:else}
  system
{/if}
