<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAnchorAttributes } from 'svelte/elements';
	import { resolveHref } from '$lib/utils';
	import Button from './Button.svelte';

	let {
		children,
		href,
		...rest
	}: HTMLAnchorAttributes & {
		children: Snippet;
		href: string;
	} = $props();
</script>

<Button tag="a" href={resolveHref(href)} {...rest}>{@render children()}</Button>
