<script lang="ts">
  import client from '$lib/api/client';
  import { createAsyncLoader } from '$lib/async-loader.svelte';
  import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

  const loader = createAsyncLoader(async () => {
    const { data } = await client.GET('/api/game-formats/');
    return data ?? [];
  }, []);
</script>

<TaxonomyListPage
  catalogKey="game-format"
  items={loader.data}
  loading={loader.loading}
  error={loader.error}
  canCreate
>
  {#snippet headerSnippet()}
    <p class="overview">
      A <strong>game format</strong> is the broad category of play a machine belongs to — the
      physical vocabulary of how a ball (or puck) moves and how the player interacts with it.
      <a href="/game-formats/pinball">Pinball</a> is the dominant format and the reason this catalog
      exists: a tilted playfield, a plunger, and — since
      <a href="/manufacturers/gottlieb">Gottlieb</a>'s
      <a href="/titles/humpty-dumpty"><em>Humpty Dumpty</em></a> in 1947 — flippers. It descends
      directly from <a href="/game-formats/bagatelle">bagatelle</a>, the flipperless
      plunger-and-gravity ancestor that established the basic form.
      <a href="/game-formats/shuffle">Shuffle</a> alleys (pucks slid down a long lane toward pins or
      scoring zones) and <a href="/game-formats/pitch-and-bat">pitch-and-bat</a> baseball games
      shared manufacturers, operators, and distribution with pinball —
      <a href="/manufacturers/williams">Williams</a>
      and <a href="/manufacturers/chicago-coin">Chicago Coin</a> built all of them — but occupied different
      niches on the coin-op route.
    </p>
  {/snippet}
</TaxonomyListPage>

<style>
  .overview {
    font-size: var(--font-size-2);
    color: var(--color-text-muted);
    margin-top: var(--size-2);
    max-width: 42rem;
    line-height: 1.5;
  }

  .overview a {
    color: var(--color-link);
  }
</style>
