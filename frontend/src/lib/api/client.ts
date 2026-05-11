import createClient from 'openapi-fetch';
import type { paths } from './schema';

export function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match?.[1];
}

// Registration slot for the 403-as-invalidation hook. The auth store
// registers a callback at module init in the browser; SSR never
// registers, so the slot stays null and the middleware below no-ops.
//
// Why a setter instead of a static import of `auth`? `auth.svelte.ts`
// imports this module for `client`/`getBrowserClient`. A direct
// `import { auth }` here would form `client → auth → client`. The
// setter inverts the runtime callback flow without forming a static
// import cycle.
let onPolicyDenied: (() => void) | null = null;
export function registerOnPolicyDenied(cb: () => void): void {
  onPolicyDenied = cb;
}

export function createApiClient(
  fetchImpl: typeof fetch = fetch,
  baseUrl = '',
  incomingRequest?: Request,
) {
  const client = createClient<paths>({
    baseUrl,
    fetch: fetchImpl,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // SvelteKit's event.fetch only forwards cookies for same-origin requests.
  // When INTERNAL_API_BASE_URL points SSR at Django on a different origin
  // (e.g. http://127.0.0.1:8000 in prod), we must forward the user's Cookie
  // header manually or authenticated endpoints see an anonymous request.
  const forwardedCookie = incomingRequest?.headers.get('cookie') ?? null;

  client.use({
    async onRequest({ request }) {
      // openapi-fetch percent-encodes `/` in path params, breaking Django's `:path`
      // converter for multi-segment public_ids. `/` is reserved, so `%2F` in pathname is always ours to decode.
      const url = new URL(request.url);
      const decoded = url.pathname.replace(/%2[Ff]/g, '/');
      if (decoded !== url.pathname) {
        url.pathname = decoded;
        request = new Request(url, request);
      }

      if (forwardedCookie) {
        request.headers.set('cookie', forwardedCookie);
      }

      const method = request.method.toUpperCase();
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const token = getCsrfToken();
        if (token) {
          request.headers.set('X-CSRFToken', token);
        }
      }
      return request;
    },
    async onResponse({ response }) {
      // 403-as-invalidation: when the server denies an action the
      // SPA's stored capabilities thought was allowed, refetch /me/
      // to refresh the verdicts. Allow→deny direction only — the
      // reverse direction (capability newly granted) is covered by
      // explicit `auth.refresh()` on auth mutations.
      if (response.status !== 403 || !onPolicyDenied) return;
      try {
        const body = await response.clone().json();
        if (body?.detail?.kind === 'policy_denied') onPolicyDenied();
      } catch {
        // Body wasn't JSON or didn't match — ignore.
      }
    },
  });

  return client;
}

let browserClient: ReturnType<typeof createApiClient> | null = null;

function getBrowserClient() {
  if (typeof window === 'undefined') {
    throw new Error(
      'The default API client is browser-only. Server-side routes must use createServerClient(fetch, url, request) from $lib/api/server instead.',
    );
  }
  browserClient ??= createApiClient(window.fetch.bind(window));
  return browserClient;
}

// SSR-safe: importing this module does NOT trigger getBrowserClient().
// The Proxy defers the browser check to property-access time (client.GET(...)),
// which only happens in event handlers and $effect — never during server render.
// Do not replace this Proxy with a direct createApiClient() call at module scope.
const client = new Proxy({} as ReturnType<typeof createApiClient>, {
  get(_target, prop, receiver) {
    return Reflect.get(getBrowserClient(), prop, receiver);
  },
});

export default client;
