<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children }: { children: Snippet } = $props();
</script>

<ul class="list">{@render children()}</ul>

<style>
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
</style>
