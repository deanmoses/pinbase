import { describe, expect, it } from 'vitest';
import client from './client';

describe('default api client', () => {
  it('throws if the default client is used on the server', () => {
    expect(() => client.GET).toThrow(
      'The default API client is browser-only. Server-side routes must use createServerClient(fetch, url, request) from $lib/api/server instead.',
    );
  });
});
