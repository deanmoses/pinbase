<script lang="ts">
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { faBars, faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';
  import FaIcon from './FaIcon.svelte';
  import CoffeeStain from './effects/CoffeeStain.svelte';
  import ActionMenu from './ActionMenu.svelte';
  import MenuItem from './MenuItem.svelte';
  import MenuSectionHeader from './MenuSectionHeader.svelte';
  import MenuDivider from './MenuDivider.svelte';
  import Avatar from './Avatar.svelte';
  import { SITE_NAME, NARROW_BREAKPOINT } from '$lib/constants';
  import { resolveHref } from '$lib/utils';
  import { auth } from '$lib/auth.svelte';
  import { createBelowBreakpointFlag } from '$lib/use-below-breakpoint.svelte';
  import { toast } from '$lib/toast/toast.svelte';

  const navItems = [
    { href: '/titles' as const, label: 'Titles' },
    { href: '/manufacturers' as const, label: 'Manufacturers' },
    { href: '/people' as const, label: 'People' },
  ];
  const changelogHref = '/changesets' as const;

  function isActive(href: string) {
    return page.url.pathname.startsWith(href);
  }

  // Mirrors the `(--breakpoint-narrow)` CSS tier below. Used to decide
  // whether the hamburger menu duplicates the primary nav items — tablet
  // keeps them in the bar, mobile collapses them in.
  const isMobileFlag = createBelowBreakpointFlag(NARROW_BREAKPOINT);
  const isMobile = $derived(isMobileFlag.current === true);

  $effect(() => {
    auth.load();
  });

  async function handleLogout() {
    await auth.logout();
    toast.success('Signed out');
  }

  function loginHref() {
    return `/api/auth/login/?next=${encodeURIComponent(page.url.pathname)}`;
  }

  const myContributionsHref = $derived(resolveHref(`/users/${auth.username}`));
  const myContributionsActive = $derived(isActive(`/users/${auth.username}`));

  const randInt = (max: number) => Math.floor(Math.random() * max);

  // Stain seeds (one per stain strip)
  const stainSeed1 = randInt(1000);
  const stainSeed2 = randInt(1000);
  const stainSeed3 = randInt(1000);

  // Torn bottom edge
  const tornId = `tear-${crypto.randomUUID()}`;
  const tornSeed = randInt(1000);
</script>

<!-- Torn edge filter definition -->
<svg class="svg-filters" aria-hidden="true">
  <defs>
    <filter id={tornId} x="-2%" y="-2%" width="104%" height="120%">
      <feTurbulence
        type="turbulence"
        baseFrequency="0.06 0.02"
        numOctaves="4"
        seed={tornSeed}
        result="warp"
      />
      <feDisplacementMap in="SourceGraphic" in2="warp" scale="6" yChannelSelector="R" />
    </filter>
  </defs>
</svg>

<header class="site-header">
  <div class="header-inner">
    <a href={resolve('/')} class="site-title">{SITE_NAME}</a>

    {#snippet adminSection()}
      <MenuSectionHeader>admin</MenuSectionHeader>
      <MenuItem href={resolve('/kiosk/configure')} current={isActive('/kiosk/configure')}>
        Kiosk Config
      </MenuItem>
      <MenuItem href="/admin/" reload>Django Admin</MenuItem>
    {/snippet}

    {#snippet userSection()}
      <MenuSectionHeader>{auth.username}</MenuSectionHeader>
      <MenuItem href={myContributionsHref} current={myContributionsActive}>
        My Contributions
      </MenuItem>
      <MenuItem onclick={handleLogout}>Sign Out</MenuItem>
    {/snippet}

    <nav class="primary-nav" aria-label="Primary">
      {#each navItems as { href, label } (href)}
        <a href={resolve(href)} class="nav-link" class:active={isActive(href)}>
          {label}
        </a>
      {/each}
      <a
        href={resolve(changelogHref)}
        class="nav-link changelog-link"
        class:active={isActive(changelogHref)}
      >
        Changelog
      </a>
    </nav>

    <div class="header-actions">
      <a
        href={resolveHref('/search')}
        class="search-link"
        class:active={isActive('/search')}
        aria-label="Search"
      >
        <FaIcon icon={faMagnifyingGlass} size="1.1rem" />
      </a>

      {#if auth.loaded}
        <div class="desktop-account">
          {#if auth.isAuthenticated}
            <ActionMenu label="Account" variant="bare" ariaLabel="Account menu">
              {#snippet trigger()}
                <Avatar
                  firstName={auth.firstName}
                  lastName={auth.lastName}
                  username={auth.username ?? ''}
                />
              {/snippet}
              {#if auth.isSuperuser}
                {@render adminSection()}
                <MenuDivider />
              {/if}
              {@render userSection()}
            </ActionMenu>
          {:else}
            <a href={loginHref()} class="auth-link" data-sveltekit-reload>Sign In</a>
          {/if}
        </div>
      {/if}

      <!-- Hamburger renders unconditionally so mobile users always have a way
           to reach Titles / Manufacturers / People, even before auth resolves.
           Auth-dependent sections inside skip rendering until auth.loaded. -->
      <div class="hamburger">
        <ActionMenu label="Menu" variant="bare" ariaLabel="Menu">
          {#snippet trigger()}
            <FaIcon icon={faBars} size="1.25rem" />
          {/snippet}
          {#if isMobile}
            {#each navItems as { href, label } (href)}
              <MenuItem href={resolve(href)} current={isActive(href)}>{label}</MenuItem>
            {/each}
            <MenuDivider />
          {/if}
          <MenuSectionHeader>activity</MenuSectionHeader>
          <MenuItem href={resolve(changelogHref)} current={isActive(changelogHref)}>
            Changelog
          </MenuItem>
          {#if auth.loaded}
            {#if auth.isSuperuser}
              <MenuDivider />
              {@render adminSection()}
            {/if}
            <MenuDivider />
            {#if auth.isAuthenticated}
              {@render userSection()}
            {:else}
              <MenuItem href={loginHref()} reload>Sign In</MenuItem>
            {/if}
          {/if}
        </ActionMenu>
      </div>
    </div>
  </div>

  <!-- Coffee stain overlays — three strips covering full width -->
  <div class="header-stains">
    <CoffeeStain
      seed={stainSeed1}
      frequency={0.03}
      opacity={0.12}
      blur={4}
      threshold="0 0 0 0 0 0 0.5 0.7"
      x="0%"
      width="40%"
    />
    <CoffeeStain
      seed={stainSeed2}
      frequency={0.04}
      octaves={4}
      opacity={0.08}
      blur={5}
      threshold="0 0 0 0 0 0 0 0.4"
      color="rgb(100, 65, 20)"
      x="30%"
      width="40%"
    />
    <CoffeeStain
      seed={stainSeed3}
      frequency={0.025}
      opacity={0.1}
      blur={3}
      threshold="0 0 0 0 0 0.4 0.6 0.8"
      color="rgb(130, 90, 35)"
      x="60%"
      width="40%"
    />
  </div>

  <!-- Torn bottom edge -->
  <div class="torn-edge" style:filter="url(#{tornId})"></div>
</header>

<style>
  .svg-filters {
    position: absolute;
    width: 0;
    height: 0;
    overflow: hidden;
    pointer-events: none;
  }

  .site-header {
    /* Color tokens — overridden in dark mode */
    --header-bg: #efe8dc;
    --header-ink: #3d3529;
    --header-ink-muted: #6b5d4d;

    position: sticky;
    top: 0;
    z-index: 100;
    background-color: var(--header-bg);
    border-bottom: none;
  }

  /* Subtle paper grain via repeating gradient */
  .site-header::before {
    content: '';
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 0, 0, 0.01) 2px,
      rgba(0, 0, 0, 0.01) 4px
    );
    pointer-events: none;
    z-index: 1;
  }

  /* Torn paper bottom edge — shares background color via token */
  .torn-edge {
    position: absolute;
    bottom: -4px;
    left: 0;
    right: 0;
    height: 8px;
    background: var(--header-bg);
    pointer-events: none;
    z-index: 3;
  }

  .header-inner {
    position: relative;
    max-width: 72rem;
    margin: 0 auto;
    padding: var(--size-3) var(--size-5);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--size-4);
    z-index: 10;
  }

  .site-title {
    font-size: var(--font-size-4);
    font-weight: 700;
    color: var(--header-ink);
    text-decoration: none;
  }

  .site-title:hover {
    color: var(--color-link);
  }

  .primary-nav {
    display: flex;
    gap: var(--size-5);
  }

  .nav-link {
    color: var(--header-ink-muted);
    text-decoration: none;
    font-size: var(--font-size-2);
    font-weight: 500;
    padding: var(--size-1) 0;
    border-bottom: 2px solid transparent;
    transition:
      color 0.15s var(--ease-2),
      border-color 0.15s var(--ease-2);
  }

  .nav-link:hover {
    color: var(--header-ink);
  }

  .nav-link.active {
    color: var(--color-link);
    border-bottom-color: var(--color-link);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: var(--size-3);
  }

  .search-link {
    color: var(--header-ink-muted);
    padding: var(--size-1);
    display: flex;
    align-items: center;
    transition: color 0.15s var(--ease-2);
  }

  .search-link:hover {
    color: var(--header-ink);
  }

  .search-link.active {
    color: var(--color-link);
  }

  .auth-link {
    font-size: var(--font-size-2);
    color: var(--header-ink-muted);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.15s var(--ease-2);
  }

  .auth-link:hover {
    color: var(--header-ink);
  }

  /* Hamburger / desktop-account wrappers: ActionMenu's `bare` trigger inherits
     color from us, so we own idle and hover styling via inheritance. The
     custom properties scale MenuItem / MenuSectionHeader densities up from
     their compact defaults, since this menu has fewer items than e.g. the
     image-category picker and doubles as the primary nav on mobile. */
  .hamburger,
  .desktop-account {
    --menu-item-font-size: var(--font-size-2);
    --menu-item-padding: var(--size-2) var(--size-4);
    --menu-section-header-font-size: 0.875rem;
    display: flex;
    align-items: center;
    color: var(--header-ink-muted);
    transition: color 0.15s var(--ease-2);
  }

  .hamburger:hover,
  .desktop-account:hover {
    color: var(--header-ink);
  }

  /* ── Three responsive tiers ──
     Narrow: only logo, search, hamburger.
     Middle band: bar shows primary nav minus Changelog, plus hamburger;
       account menu collapses into hamburger.
     Wide: full bar including Changelog and account menu; hamburger hidden. */
  .hamburger {
    display: none;
  }

  @media (--breakpoint-narrow) {
    .primary-nav {
      display: none;
    }
    .desktop-account {
      display: none;
    }
    .hamburger {
      display: flex;
    }
  }

  @media (not (--breakpoint-narrow)) and (not (--breakpoint-wide)) {
    .changelog-link {
      display: none;
    }
    .desktop-account {
      display: none;
    }
    .hamburger {
      display: flex;
    }
  }

  .header-stains {
    display: none;
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  @media (prefers-color-scheme: light) {
    .header-stains {
      display: block;
    }
  }

  /* ---- Dark mode ---- */
  @media (prefers-color-scheme: dark) {
    .site-header {
      --header-bg: #26221d;
      --header-ink: var(--color-text-primary);
      --header-ink-muted: var(--color-text-muted);
    }

    .site-header::before {
      background: none;
    }
  }
</style>
