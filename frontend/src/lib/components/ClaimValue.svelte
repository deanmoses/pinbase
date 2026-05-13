<script lang="ts">
  import { formatValue, simplifyClaimValue } from './change-display';

  let { value }: { value: unknown } = $props();

  let simple = $derived(simplifyClaimValue(value));
</script>

{#if simple}
  {#if simple.exists}
    {simple.display}
  {:else}
    <s>{simple.display}</s>
  {/if}
{:else}
  {formatValue(value)}
{/if}
