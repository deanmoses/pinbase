<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLAnchorAttributes } from 'svelte/elements';
  import { resolveHref } from '$lib/utils';
  import Button, { type ButtonVariant } from './Button.svelte';

  let {
    children,
    href,
    variant,
    fullWidth,
    ...rest
  }: HTMLAnchorAttributes & {
    children: Snippet;
    href: string;
    variant?: ButtonVariant;
    fullWidth?: boolean;
  } = $props();
</script>

<Button tag="a" href={resolveHref(href)} {variant} {fullWidth} {...rest}
  >{@render children()}</Button
>
