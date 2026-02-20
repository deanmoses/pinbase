<script lang="ts">
	import { SITE_NAME, pageTitle } from '$lib/constants';

	let scalarLoaded = $state(false);
	let scalarError = $state('');

	const scalarCustomCss = `
		.scalar-api-reference {
			--scalar-background-1: var(--color-background);
			--scalar-background-2: var(--color-surface);
			--scalar-background-3: var(--color-background);
			--scalar-color-1: var(--color-text-primary);
			--scalar-color-2: var(--color-text-muted);
			--scalar-color-3: var(--color-text-muted);
			--scalar-color-accent: var(--color-accent);
			--scalar-font: 'Lora', serif;
			--scalar-border-color: var(--color-border-soft);
		}
	`;

	$effect(() => {
		const script = document.createElement('script');
		script.src = 'https://cdn.jsdelivr.net/npm/@scalar/api-reference';
		script.onload = () => {
			// @ts-expect-error — Scalar loaded via CDN
			Scalar.createApiReference('#scalar-api-reference', {
				url: '/api/openapi.json',
				theme: 'none',
				layout: 'modern',
				showSidebar: true,
				hideClientButton: true,
				customCss: scalarCustomCss
			});
			scalarLoaded = true;
		};
		script.onerror = () => {
			scalarError = 'Failed to load API reference. Please try refreshing the page.';
		};
		document.head.appendChild(script);

		return () => {
			script.remove();
		};
	});
</script>

<svelte:head>
	<title>{pageTitle('API')}</title>
</svelte:head>

<section class="hero">
	<h1>Open Data API</h1>
	<p>{SITE_NAME} is open data. Every bit of data is available through public APIs.</p>
</section>

<section class="developer-resources">
	<div class="resource-card">
		<h3>OpenAPI Spec</h3>
		<p>
			<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- backend API path, not a SvelteKit route -->
			<a href="/api/openapi.json" target="_blank" rel="noopener">Download</a> the raw OpenAPI 3.1 specification
			to use with any compatible tooling.
		</p>
	</div>

	<div class="resource-card">
		<h3>TypeScript Types</h3>
		<p>Generate fully-typed API bindings in one command:</p>
		<pre><code>npx openapi-typescript https://flipdb.org/api/openapi.json -o schema.d.ts</code
			></pre>
	</div>
</section>

<section class="api-reference-section">
	<h2>API Reference</h2>
	{#if scalarError}
		<p class="error-message">{scalarError}</p>
	{:else if !scalarLoaded}
		<p class="loading-message">Loading API reference…</p>
	{/if}
	<div id="scalar-api-reference"></div>
</section>

<style>
	.hero {
		margin-bottom: var(--size-8);
	}

	.hero h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.hero p {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		line-height: var(--font-lineheight-3);
		max-width: 48rem;
	}

	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-4);
	}

	.api-reference-section {
		margin-bottom: var(--size-8);
	}

	.loading-message,
	.error-message {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		padding: var(--size-6) 0;
	}

	.error-message {
		color: var(--color-error);
	}

	.developer-resources {
		margin-bottom: var(--size-8);
	}

	.resource-card {
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-4) var(--size-5);
		margin-bottom: var(--size-4);
	}

	.resource-card h3 {
		font-size: var(--font-size-2);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.resource-card p {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		margin-bottom: var(--size-2);
		line-height: var(--font-lineheight-3);
	}

	pre {
		background-color: var(--color-background);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-3) var(--size-4);
		overflow-x: auto;
		font-size: var(--font-size-0);
		font-family: var(--font-mono);
	}

	code {
		font-family: var(--font-mono);
	}
</style>
