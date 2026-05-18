import { describe, expect, it } from 'vitest';
import { load } from './+page.server';

describe('/a +page.server.ts load', () => {
  it('redirects (303) to /a/dashboard', () => {
    let thrown: unknown;
    try {
      (load as unknown as () => unknown)();
    } catch (e) {
      thrown = e;
    }
    // SvelteKit's redirect() throws an object with { status, location }.
    expect(thrown).toMatchObject({ status: 303, location: '/a/dashboard' });
  });
});
