<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Action } from 'svelte/action';

	let {
		href,
		title,
		thumbnailUrl = null,
		children = undefined
	}: {
		href: string;
		title: string;
		thumbnailUrl?: string | null;
		children?: Snippet;
	} = $props();

	// Unique ID per component instance for SVG filter references
	const uid = Math.random().toString(36).slice(2, 8);

	// Random seeds for SVG turbulence (each card gets different noise patterns)
	const grainSeed = Math.floor(Math.random() * 1000);
	const stainSeed = Math.floor(Math.random() * 1000);
	const stainSeed2 = Math.floor(Math.random() * 1000);

	// Randomize stain blob position (as fraction 0–1)
	const stainX = 0.15 + Math.random() * 0.7;
	const stainY = 0.15 + Math.random() * 0.7;
	const stain2X = 0.1 + Math.random() * 0.8;
	const stain2Y = 0.1 + Math.random() * 0.8;

	// Wear effect: ~40% of cards get a dog-ear, crease, or torn corner
	type WearType = 'none' | 'dog-ear' | 'crease' | 'torn-corner';
	const wearRoll = Math.random();
	const wearType: WearType =
		wearRoll < 0.6
			? 'none'
			: wearRoll < 0.73
				? 'dog-ear'
				: wearRoll < 0.87
					? 'crease'
					: 'torn-corner';

	// Which corner for dog-ear / torn-corner (top-right, top-left, bottom-right, bottom-left)
	const corners = ['tr', 'tl', 'br', 'bl'] as const;
	const wearCorner = corners[Math.floor(Math.random() * corners.length)];

	// Crease angle and position
	const creaseAngle = -25 + Math.random() * 50; // -25° to 25°
	const creasePos = 30 + Math.random() * 40; // 30%–70% from top

	// Dog-ear size
	const earSize = 1 + Math.random() * 0.8; // 1rem to 1.8rem

	/**
	 * Svelte action that assigns random CSS custom properties to each card,
	 * giving every polaroid a unique aged/worn appearance.
	 */
	const polaroid: Action = (node) => {
		const rand = (min: number, max: number) => Math.random() * (max - min) + min;

		// Slight random rotation for that pinned-to-a-board feel
		node.style.setProperty('--rotation', `${rand(-3, 3)}deg`);

		// Faded photo: randomize sepia/brightness/contrast
		node.style.setProperty('--sepia', `${rand(0.3, 0.7)}`);
		node.style.setProperty('--brightness', `${rand(0.9, 1.05)}`);
		node.style.setProperty('--contrast', `${rand(0.85, 0.95)}`);
		node.style.setProperty('--saturate', `${rand(0.6, 0.85)}`);

		// Yellowed paper tint intensity
		node.style.setProperty('--paper-yellow', `${rand(0.03, 0.08)}`);
	};
</script>

<!-- Hidden SVG filter definitions (one per card instance) -->
<svg class="svg-filters" aria-hidden="true">
	<defs>
		<!-- Film grain overlay for the photo -->
		<filter id="grain-{uid}" x="0%" y="0%" width="100%" height="100%">
			<feTurbulence
				type="fractalNoise"
				baseFrequency="0.7"
				numOctaves="3"
				seed={grainSeed}
				result="grain"
			/>
			<feColorMatrix type="saturate" values="0" in="grain" result="grainMono" />
			<feBlend in="SourceGraphic" in2="grainMono" mode="multiply" />
		</filter>

		<!-- Organic coffee stain blob -->
		<filter id="stain-{uid}" x="-50%" y="-50%" width="200%" height="200%">
			<feTurbulence
				type="fractalNoise"
				baseFrequency="0.035"
				numOctaves="5"
				seed={stainSeed}
				result="noise"
			/>
			<feComponentTransfer in="noise" result="blobs">
				<feFuncA type="discrete" tableValues="0 0 0 0 0 0 0.6 0.8" />
			</feComponentTransfer>
			<feFlood flood-color="rgb(120, 80, 30)" flood-opacity="0.15" result="color" />
			<feComposite in="color" in2="blobs" operator="in" result="stain" />
			<feGaussianBlur in="stain" stdDeviation="3" />
		</filter>

		<!-- Second stain with different pattern -->
		<filter id="stain2-{uid}" x="-50%" y="-50%" width="200%" height="200%">
			<feTurbulence
				type="fractalNoise"
				baseFrequency="0.045"
				numOctaves="4"
				seed={stainSeed2}
				result="noise"
			/>
			<feComponentTransfer in="noise" result="blobs">
				<feFuncA type="discrete" tableValues="0 0 0 0 0 0 0 0.5" />
			</feComponentTransfer>
			<feFlood flood-color="rgb(100, 65, 20)" flood-opacity="0.1" result="color" />
			<feComposite in="color" in2="blobs" operator="in" result="stain" />
			<feGaussianBlur in="stain" stdDeviation="4" />
		</filter>
	</defs>
</svg>

<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- href is pre-resolved by caller -->
<a {href} class="card" use:polaroid>
	<div class="card-photo">
		{#if thumbnailUrl}
			<img
				src={thumbnailUrl}
				alt=""
				class="card-img"
				loading="lazy"
				style:filter="url(#{`grain-${uid}`}) sepia(var(--sepia, 0.5)) brightness(var(--brightness,
				0.95)) contrast(var(--contrast, 0.9)) saturate(var(--saturate, 0.7))"
			/>
		{:else}
			<div class="card-img-placeholder"></div>
		{/if}
	</div>
	<div class="card-body">
		<h3 class="card-title">{title}</h3>
		{#if children}
			{@render children()}
		{/if}
	</div>
	<!-- SVG stain overlays with organic shapes -->
	<svg class="stain-overlay" aria-hidden="true">
		<rect
			x="{(stainX - 0.2) * 100}%"
			y="{(stainY - 0.2) * 100}%"
			width="40%"
			height="40%"
			filter="url(#{`stain-${uid}`})"
		/>
		<rect
			x="{(stain2X - 0.15) * 100}%"
			y="{(stain2Y - 0.15) * 100}%"
			width="30%"
			height="30%"
			filter="url(#{`stain2-${uid}`})"
		/>
	</svg>

	<!-- Wear effects: dog-ear, crease, or torn corner -->
	{#if wearType === 'dog-ear'}
		<div class="dog-ear dog-ear--{wearCorner}" style:--ear-size="{earSize}rem"></div>
	{:else if wearType === 'crease'}
		<div
			class="crease"
			style:--crease-angle="{creaseAngle}deg"
			style:--crease-pos="{creasePos}%"
		></div>
	{:else if wearType === 'torn-corner'}
		<div class="torn-corner torn-corner--{wearCorner}"></div>
	{/if}
</a>

<style>
	.svg-filters {
		position: absolute;
		width: 0;
		height: 0;
		overflow: hidden;
		pointer-events: none;
	}

	.card {
		position: relative;
		display: flex;
		flex-direction: column;
		background-color: #faf6f0;
		border: none;
		border-radius: 2px;
		overflow: visible;
		text-decoration: none;
		color: inherit;
		padding: 0.6rem 0.6rem 1.6rem;
		transform: rotate(var(--rotation, 0deg));
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.12),
			0 4px 8px rgba(0, 0, 0, 0.06);
		transition:
			transform 0.2s ease,
			box-shadow 0.2s ease;
	}

	/* Yellowed paper tint overlay */
	.card::before {
		content: '';
		position: absolute;
		inset: 0;
		background: rgba(180, 150, 80, var(--paper-yellow, 0.05));
		pointer-events: none;
		border-radius: 2px;
		z-index: 2;
	}

	.card:hover {
		transform: rotate(0deg) scale(1.03);
		box-shadow:
			0 4px 12px rgba(0, 0, 0, 0.15),
			0 8px 20px rgba(0, 0, 0, 0.08);
		z-index: 1;
	}

	/* Organic coffee stain SVG overlay */
	.stain-overlay {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
		z-index: 3;
		border-radius: 2px;
		overflow: hidden;
	}

	.card-photo {
		position: relative;
		overflow: hidden;
		border-radius: 1px;
	}

	.card-img {
		width: 100%;
		height: 8rem;
		object-fit: cover;
	}

	.card-img-placeholder {
		width: 100%;
		height: 8rem;
		background-color: #e8e0d4;
	}

	.card-body {
		padding: var(--size-3) 0 0;
	}

	.card-title {
		font-size: var(--font-size-2);
		font-weight: 600;
		color: #3d3529;
		margin-bottom: var(--size-1);
	}

	/* =============================================
	   DOG-EAR: folded corner triangle
	   ============================================= */
	.dog-ear {
		position: absolute;
		width: var(--ear-size, 1.4rem);
		height: var(--ear-size, 1.4rem);
		pointer-events: none;
		z-index: 4;
		overflow: hidden;
	}

	/* The fold itself: a triangle that looks like paper folded over */
	.dog-ear::before {
		content: '';
		position: absolute;
		width: 100%;
		height: 100%;
		background: linear-gradient(
			135deg,
			rgba(0, 0, 0, 0.06) 0%,
			rgba(0, 0, 0, 0.02) 50%,
			#e8e0d0 50%,
			#ded5c4 100%
		);
	}

	/* Shadow beneath the fold */
	.dog-ear::after {
		content: '';
		position: absolute;
		width: 140%;
		height: 140%;
		background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.1) 0%, transparent 70%);
	}

	/* Position each corner variant */
	.dog-ear--tr {
		top: 0;
		right: 0;
	}
	.dog-ear--tr::before {
		background: linear-gradient(
			225deg,
			rgba(0, 0, 0, 0.06) 0%,
			rgba(0, 0, 0, 0.02) 50%,
			#e8e0d0 50%,
			#ded5c4 100%
		);
	}
	.dog-ear--tr::after {
		bottom: -20%;
		left: -20%;
	}

	.dog-ear--tl {
		top: 0;
		left: 0;
	}
	.dog-ear--tl::before {
		background: linear-gradient(
			315deg,
			rgba(0, 0, 0, 0.06) 0%,
			rgba(0, 0, 0, 0.02) 50%,
			#e8e0d0 50%,
			#ded5c4 100%
		);
	}
	.dog-ear--tl::after {
		bottom: -20%;
		right: -20%;
	}

	.dog-ear--br {
		bottom: 0;
		right: 0;
	}
	.dog-ear--br::before {
		background: linear-gradient(
			135deg,
			#e8e0d0 0%,
			#ded5c4 50%,
			rgba(0, 0, 0, 0.02) 50%,
			rgba(0, 0, 0, 0.06) 100%
		);
	}
	.dog-ear--br::after {
		top: -20%;
		left: -20%;
	}

	.dog-ear--bl {
		bottom: 0;
		left: 0;
	}
	.dog-ear--bl::before {
		background: linear-gradient(
			45deg,
			rgba(0, 0, 0, 0.06) 0%,
			rgba(0, 0, 0, 0.02) 50%,
			#e8e0d0 50%,
			#ded5c4 100%
		);
	}
	.dog-ear--bl::after {
		top: -20%;
		right: -20%;
	}

	/* =============================================
	   CREASE: diagonal fold line across the card
	   ============================================= */
	.crease {
		position: absolute;
		left: -5%;
		right: -5%;
		top: var(--crease-pos, 50%);
		height: 2px;
		pointer-events: none;
		z-index: 4;
		transform: rotate(var(--crease-angle, 0deg));
		transform-origin: center;
	}

	/* Main crease line */
	.crease::before {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(
			to right,
			transparent 0%,
			rgba(0, 0, 0, 0.08) 15%,
			rgba(0, 0, 0, 0.12) 50%,
			rgba(0, 0, 0, 0.08) 85%,
			transparent 100%
		);
	}

	/* Highlight along one side of crease (paper catching light) */
	.crease::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: -1px;
		height: 1px;
		background: linear-gradient(
			to right,
			transparent 0%,
			rgba(255, 255, 255, 0.15) 20%,
			rgba(255, 255, 255, 0.25) 50%,
			rgba(255, 255, 255, 0.15) 80%,
			transparent 100%
		);
	}

	/* =============================================
	   TORN CORNER: ragged missing piece
	   ============================================= */
	.torn-corner {
		position: absolute;
		width: 1.6rem;
		height: 1.6rem;
		pointer-events: none;
		z-index: 4;
		overflow: hidden;
	}

	/*
	 * The torn effect: a jagged-edged shape that matches the page
	 * background color, masking out the card corner.
	 * Uses a polygon clip-path for the rough tear line.
	 */
	.torn-corner::before {
		content: '';
		position: absolute;
		width: 100%;
		height: 100%;
		background: var(--color-background, #f5f5f5);
		clip-path: polygon(
			0% 0%,
			100% 0%,
			85% 15%,
			95% 30%,
			75% 45%,
			90% 55%,
			70% 70%,
			80% 85%,
			60% 100%,
			0% 100%
		);
	}

	/* Subtle shadow along the tear edge */
	.torn-corner::after {
		content: '';
		position: absolute;
		width: 100%;
		height: 100%;
		background: linear-gradient(135deg, transparent 40%, rgba(0, 0, 0, 0.1) 60%, transparent 80%);
	}

	.torn-corner--tr {
		top: 0;
		right: 0;
		transform: rotate(90deg);
	}

	.torn-corner--tl {
		top: 0;
		left: 0;
	}

	.torn-corner--br {
		bottom: 0;
		right: 0;
		transform: rotate(180deg);
	}

	.torn-corner--bl {
		bottom: 0;
		left: 0;
		transform: rotate(270deg);
	}

	/* ---- Dark mode: aged polaroid on a dark surface ---- */
	@media (prefers-color-scheme: dark) {
		.card {
			background-color: #2e2a24;
			box-shadow:
				0 1px 3px rgba(0, 0, 0, 0.4),
				0 4px 8px rgba(0, 0, 0, 0.25);
		}

		.card::before {
			background: rgba(140, 110, 60, var(--paper-yellow, 0.05));
		}

		.card:hover {
			box-shadow:
				0 4px 12px rgba(0, 0, 0, 0.4),
				0 8px 20px rgba(0, 0, 0, 0.3);
		}

		.card-img-placeholder {
			background-color: #3a342b;
		}

		.card-title {
			color: #c8bfb0;
		}

		/* Dog-ear: darker fold colors */
		.dog-ear--tr::before,
		.dog-ear--tl::before,
		.dog-ear--br::before,
		.dog-ear--bl::before {
			filter: brightness(0.5);
		}

		/* Torn corner: reveal dark background */
		.torn-corner::before {
			background: var(--color-background, #1f1f1f);
		}

		/* Crease: invert highlight/shadow for dark paper */
		.crease::before {
			background: linear-gradient(
				to right,
				transparent 0%,
				rgba(0, 0, 0, 0.15) 15%,
				rgba(0, 0, 0, 0.2) 50%,
				rgba(0, 0, 0, 0.15) 85%,
				transparent 100%
			);
		}
		.crease::after {
			background: linear-gradient(
				to right,
				transparent 0%,
				rgba(255, 255, 255, 0.06) 20%,
				rgba(255, 255, 255, 0.1) 50%,
				rgba(255, 255, 255, 0.06) 80%,
				transparent 100%
			);
		}
	}
</style>
