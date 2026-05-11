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
  /** Padding from the viewport edge for `flip`/`shift`/`size`, in px. */
  padding?: number;
  /** Set the floating element's width to match the anchor's width. */
  matchAnchorWidth?: boolean;
  /**
   * Constrain the floating element's max-height. `'available'` fits it to the
   * remaining viewport space along the placement axis (so a dropdown near the
   * bottom shrinks instead of overflowing). A number sets a fixed px cap.
   */
  maxHeight?: 'available' | number;
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

  // Park the element far offscreen until the first computePosition resolves,
  // to avoid a top-left flash while the dynamic floating-ui import is loading.
  // We deliberately do NOT use visibility/opacity/pointer-events to hide:
  //   - visibility:hidden removes the element from the a11y tree (testing-
  //     library's getByRole skips it).
  //   - opacity:0 keeps it in the a11y tree but leaves it clickable at (0,0),
  //     and pointer-events:none on the parent doesn't help — menu items are
  //     children with `auto` and would still be hit (and it trips up
  //     @testing-library/user-event, which refuses to interact with any
  //     descendant of a pointer-events:none ancestor).
  // Offscreen positioning sidesteps all of that: the element remains
  // measurable for computePosition and stays in the a11y tree, but a real
  // pointer can't reach it.
  node.style.position = 'fixed';
  node.style.top = '-9999px';
  node.style.left = '0';

  const portalTarget = findPortalTarget(node);
  portalTarget.appendChild(node);

  function reposition() {
    if (!fui) return;
    const opts = currentOptions;
    const padding = opts.padding ?? 8;
    const middleware = [
      fui.offset(opts.offset ?? 4),
      fui.flip({ padding }),
      fui.shift({ padding }),
    ];

    if (opts.matchAnchorWidth || opts.maxHeight != null) {
      middleware.push(
        fui.size({
          padding,
          apply({ rects, availableHeight }) {
            if (opts.matchAnchorWidth) {
              node.style.width = `${rects.reference.width}px`;
            }
            if (opts.maxHeight === 'available') {
              node.style.maxHeight = `${Math.max(0, Math.floor(availableHeight))}px`;
            } else if (typeof opts.maxHeight === 'number') {
              node.style.maxHeight = `${Math.min(opts.maxHeight, Math.floor(availableHeight))}px`;
            }
          },
        }),
      );
    }

    void fui
      .computePosition(opts.anchor, node, {
        placement: opts.placement ?? 'bottom-start',
        strategy: 'fixed',
        middleware,
      })
      .then(({ x, y }) => {
        if (destroyed) return;
        node.style.top = '0';
        node.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
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
