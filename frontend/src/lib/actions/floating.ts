/**
 * Svelte action that portals an element out of its original location and
 * positions it relative to an anchor (DOM element or virtual reference) using
 * Floating UI.
 *
 * Solves two problems at once:
 * 1. Portaling escapes ancestor `overflow: hidden` clipping (e.g. inside Modal).
 * 2. Floating UI handles flip/shift/size so dropdowns stay in the viewport.
 *
 * The portal target is the topmost element under `<body>` that contains the
 * node — i.e. the Svelte mount root — so delegated event handlers
 * (`onclick`, `onkeydown`, etc.) on the portaled subtree continue to fire.
 *
 * `@floating-ui/dom` is dynamically imported so anonymous readers don't pay for
 * code that only editors hit.
 */

import type { Action } from 'svelte/action';

type VirtualElement = {
  getBoundingClientRect: () => DOMRect;
  contextElement?: Element;
};

type FloatingUiModule = typeof import('@floating-ui/dom');

export type FloatingAnchor = Element | VirtualElement;

export type FloatingOptions = {
  anchor: FloatingAnchor;
  placement?:
    | 'top'
    | 'top-start'
    | 'top-end'
    | 'bottom'
    | 'bottom-start'
    | 'bottom-end'
    | 'left'
    | 'left-start'
    | 'left-end'
    | 'right'
    | 'right-start'
    | 'right-end';
  /** Gap between anchor and floating element, in px. */
  offset?: number;
  /** Padding from the viewport edge for `flip`/`shift`, in px. */
  padding?: number;
};

let modulePromise: Promise<FloatingUiModule> | undefined;
function loadFloatingUi(): Promise<FloatingUiModule> {
  modulePromise ??= import('@floating-ui/dom');
  return modulePromise;
}

function findPortalTarget(node: Element): HTMLElement {
  let el: Element = node;
  while (el.parentElement && el.parentElement !== document.body) {
    el = el.parentElement;
  }
  return (el.parentElement === document.body ? el : document.body) as HTMLElement;
}

export const floating: Action<HTMLElement, FloatingOptions> = (node, options) => {
  let currentOptions = options;
  let destroyed = false;
  let fui: FloatingUiModule | undefined;
  let cleanupAutoUpdate: (() => void) | undefined;
  let subscribedAnchor: FloatingAnchor | undefined;

  // Hide until the first position resolves to avoid a top-left flash on first
  // open (the dynamic import is async, so the floating element would otherwise
  // be visible briefly at translate(0,0) before computePosition runs).
  const originalVisibility = node.style.visibility;
  node.style.visibility = 'hidden';
  node.style.position = 'fixed';
  node.style.top = '0';
  node.style.left = '0';

  const portalTarget = findPortalTarget(node);
  portalTarget.appendChild(node);

  function reposition() {
    if (!fui) return;
    const opts = currentOptions;
    const middleware = [
      fui.offset(opts.offset ?? 4),
      fui.flip({ padding: opts.padding ?? 8 }),
      fui.shift({ padding: opts.padding ?? 8 }),
    ];

    void fui
      .computePosition(opts.anchor, node, {
        placement: opts.placement ?? 'bottom-start',
        strategy: 'fixed',
        middleware,
      })
      .then(({ x, y }) => {
        if (destroyed) return;
        node.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
        node.style.visibility = originalVisibility;
      });
  }

  function subscribe() {
    if (!fui) return;
    cleanupAutoUpdate?.();
    subscribedAnchor = currentOptions.anchor;
    cleanupAutoUpdate = fui.autoUpdate(subscribedAnchor, node, reposition);
  }

  void loadFloatingUi().then((mod) => {
    if (destroyed) return;
    fui = mod;
    subscribe();
  });

  return {
    update(next: FloatingOptions) {
      currentOptions = next;
      if (next.anchor !== subscribedAnchor) {
        subscribe();
      } else {
        reposition();
      }
    },
    destroy() {
      destroyed = true;
      cleanupAutoUpdate?.();
      if (node.parentElement === portalTarget) {
        node.remove();
      }
    },
  };
};
