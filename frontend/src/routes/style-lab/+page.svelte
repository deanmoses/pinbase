<script lang="ts">
  import ActionMenu from '$lib/components/ActionMenu.svelte';
  import Button from '$lib/components/Button.svelte';
  import MenuDivider from '$lib/components/MenuDivider.svelte';
  import MenuItem from '$lib/components/MenuItem.svelte';
  import MenuSectionHeader from '$lib/components/MenuSectionHeader.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
  import Card, {
    type CardDistressCorner,
    type CardDistressType,
  } from '$lib/components/cards/Card.svelte';
  import MachineCard from '$lib/components/cards/MachineCard.svelte';

  const distressCases: {
    label: string;
    type: CardDistressType;
    corner: CardDistressCorner;
  }[] = [
    { label: 'Torn top left', type: 'torn-corner', corner: 'tl' },
    { label: 'Torn top right', type: 'torn-corner', corner: 'tr' },
    { label: 'Torn bottom left', type: 'torn-corner', corner: 'bl' },
    { label: 'Torn bottom right', type: 'torn-corner', corner: 'br' },
    { label: 'Dog ear top left', type: 'dog-ear', corner: 'tl' },
    { label: 'Dog ear top right', type: 'dog-ear', corner: 'tr' },
    { label: 'Dog ear bottom left', type: 'dog-ear', corner: 'bl' },
    { label: 'Dog ear bottom right', type: 'dog-ear', corner: 'br' },
  ];
</script>

<div class="lab-header">
  <PageHeader
    title="Style Lab"
    subtitle="Representative UI specimens for judging palette and texture changes."
  />
  <div class="theme-control">
    <ThemeSwitcher />
  </div>
</div>

<div class="style-lab">
  <section class="specimen">
    <div class="section-heading">
      <h2>Reference Search</h2>
      <p>Primary content, links, buttons, and form controls.</p>
    </div>

    <div class="search-panel">
      <label for="lab-search">Catalog search</label>
      <div class="search-row">
        <input id="lab-search" type="search" value="bally space invaders" />
        <Button>Search</Button>
      </div>
      <p>
        Match results across <a href="/titles">titles</a>, manufacturers, people, systems, and
        gameplay features.
      </p>
    </div>
  </section>

  <section class="specimen">
    <div class="section-heading">
      <h2>Detail Surface</h2>
      <p>Dense record content with status chips and sidebar treatment.</p>
    </div>

    <div class="detail-shell">
      <article class="record-panel">
        <div class="record-kicker">Machine model</div>
        <h3>Attack from Mars</h3>
        <p>
          A widebody-feeling fan favorite with saucers, martians, stroke-heavy callouts, and
          unusually broad collector recognition.
        </p>
        <div class="chip-row" aria-label="Metadata">
          <span>Williams</span>
          <span>1995</span>
          <span>Solid state</span>
        </div>
      </article>

      <aside class="sidebar-panel">
        <h3>Claims</h3>
        <dl>
          <div>
            <dt>Status</dt>
            <dd>Reviewed</dd>
          </div>
          <div>
            <dt>Sources</dt>
            <dd>IPDB, flyers, operator manual</dd>
          </div>
        </dl>
      </aside>
    </div>
  </section>

  <section class="specimen">
    <div class="section-heading">
      <h2>System States</h2>
      <p>Feedback colors, menu surface, and secondary actions.</p>
    </div>

    <div class="states-grid">
      <div class="status-card success">Saved changes to manufacturer claims.</div>
      <div class="status-card warning">Three citations need locator details.</div>
      <div class="status-card error">Slug conflicts with an existing record.</div>
      <div class="action-cluster">
        <Button variant="secondary">Cancel</Button>
        <Button>Save changes</Button>
        <ActionMenu label="Actions">
          <MenuSectionHeader>record</MenuSectionHeader>
          <MenuItem>View sources</MenuItem>
          <MenuItem>Open edit history</MenuItem>
          <MenuDivider />
          <MenuItem>Request review</MenuItem>
        </ActionMenu>
      </div>
    </div>
  </section>
  <section class="specimen">
    <div class="section-heading">
      <h2>Catalog Cards</h2>
      <p>Polaroid cards, muted metadata, and link contrast.</p>
    </div>

    <div class="card-grid">
      <MachineCard
        slug="go-go"
        name="Go Go"
        thumbnailUrl="/fakes/fake_backglass1.avif"
        manufacturerName="Williams"
        year={1966}
      />
      <MachineCard
        slug="critters"
        name="Critters"
        thumbnailUrl="/fakes/fake_backglass2.avif"
        manufacturerName="Jersey Jack"
        year={2023}
      />
      <MachineCard
        slug="astro-blitz"
        name="Astro Blitz"
        thumbnailUrl="/fakes/fake_backglass3.avif"
        manufacturerName="Williams"
        year={1982}
      />
    </div>
  </section>

  <section class="specimen">
    <div class="section-heading">
      <h2>Torn Surfaces</h2>
      <p>Forced wear-effect variants for visually debugging every distressed card corner.</p>
    </div>

    <div class="distress-grid">
      {#each distressCases as distressCase (distressCase.label)}
        <Card
          href="/style-lab"
          title={distressCase.label}
          distressType={distressCase.type}
          distressCorner={distressCase.corner}
          distressEarSize={1.7}
        >
          <p class="distress-note">{distressCase.type} · {distressCase.corner}</p>
        </Card>
      {/each}
      <Card
        href="/style-lab"
        title="Crease"
        distressType="crease"
        distressCorner="tl"
        distressCreaseAngle={-16}
        distressCreasePos={44}
      >
        <p class="distress-note">crease · fixed angle</p>
      </Card>
    </div>
  </section>
</div>

<style>
  .style-lab {
    display: grid;
    gap: var(--size-7);
  }

  .lab-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--size-5);
  }

  .theme-control {
    display: flex;
    align-items: center;
    gap: var(--size-2);
    color: var(--color-text-muted);
    font-size: var(--font-size-1);
  }

  .specimen {
    display: grid;
    gap: var(--size-4);
  }

  .section-heading {
    max-width: 42rem;
  }

  .section-heading h2 {
    font-size: var(--font-size-4);
    margin-bottom: var(--size-1);
  }

  .section-heading p,
  .search-panel p,
  .record-panel p {
    color: var(--color-text-muted);
    line-height: 1.55;
  }

  .search-panel,
  .record-panel,
  .sidebar-panel,
  .status-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
    box-shadow: var(--shadow-card);
  }

  .search-panel {
    padding: var(--size-5);
    display: grid;
    gap: var(--size-3);
  }

  .search-panel label {
    font-weight: 600;
    color: var(--color-text);
  }

  .search-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--size-3);
    align-items: center;
  }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--size-4);
  }

  .distress-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--size-4);
  }

  .distress-note {
    color: var(--color-text-muted);
    font-size: var(--font-size-0);
  }

  .detail-shell {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(16rem, 1fr);
    gap: var(--size-4);
  }

  .record-panel,
  .sidebar-panel {
    padding: var(--size-5);
  }

  .record-kicker {
    color: var(--color-link);
    font-size: var(--font-size-0);
    font-weight: 700;
    margin-bottom: var(--size-2);
    text-transform: uppercase;
  }

  .record-panel h3,
  .sidebar-panel h3 {
    font-size: var(--font-size-4);
    margin-bottom: var(--size-2);
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--size-2);
    margin-top: var(--size-4);
  }

  .chip-row span {
    background: var(--color-accent-soft);
    border: 1px solid var(--color-accent-border);
    border-radius: var(--radius-2);
    color: var(--color-link);
    font-size: var(--font-size-0);
    font-weight: 600;
    padding: var(--size-1) var(--size-2);
  }

  .sidebar-panel dl {
    display: grid;
    gap: var(--size-3);
  }

  .sidebar-panel div {
    border-top: 1px solid var(--color-border-soft);
    padding-top: var(--size-3);
  }

  .sidebar-panel dt {
    color: var(--color-text-muted);
    font-size: var(--font-size-0);
    margin-bottom: var(--size-1);
  }

  .sidebar-panel dd {
    color: var(--color-text);
  }

  .states-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--size-3);
  }

  .status-card {
    padding: var(--size-4);
    font-weight: 600;
  }

  .success {
    background: var(--color-success-bg);
    border-color: var(--color-success-border);
    color: var(--color-success-text);
  }

  .warning {
    background: var(--color-warning-bg);
    border-color: var(--color-warning-border);
    color: var(--color-warning-text);
  }

  .error {
    background: var(--color-error-bg);
    border-color: var(--color-error-border);
    color: var(--color-error-text);
  }

  .action-cluster {
    display: flex;
    flex-wrap: wrap;
    gap: var(--size-2);
    align-items: center;
    grid-column: 1 / -1;
  }

  @media (--breakpoint-narrow) {
    .lab-header {
      display: grid;
      gap: var(--size-3);
    }

    .search-row,
    .card-grid,
    .distress-grid,
    .detail-shell,
    .states-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
