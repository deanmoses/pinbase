<script lang="ts">
  import type { ChangeSetAttributionSchema } from '$lib/api/schema';
  import ChangeSetAuthor from './ChangeSetAuthor.svelte';
  import SmartDate from './SmartDate.svelte';

  let { attribution }: { attribution: ChangeSetAttributionSchema } = $props();
</script>

<ChangeSetAuthor {attribution} />
<span aria-hidden="true">·</span>
<SmartDate iso={attribution.created_at} />
