import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { pageState } = vi.hoisted(() => ({
  pageState: {
    url: new URL('http://localhost:5173/auth/error'),
    params: {} as Record<string, string>,
  },
}));

vi.mock('$app/state', () => ({ page: pageState }));

const Page = (await import('./+page.svelte')).default;

function setReason(reason: string | null) {
  const url = new URL('http://localhost:5173/auth/error');
  if (reason !== null) url.searchParams.set('reason', reason);
  pageState.url = url;
}

beforeEach(() => {
  setReason(null);
});

describe('/auth/error', () => {
  const cases = [
    {
      reason: 'email_unverified',
      heading: 'Verify your email',
      body: 'Verify your email and try again.',
      cta: 'Try sign-in again',
      href: '/api/auth/login/',
    },
    {
      reason: 'account_conflict',
      heading: 'Account needs attention',
      body: 'Something about this account needs a human to sort out.',
      cta: 'Back to home',
      href: '/',
    },
    {
      reason: 'account_disabled',
      heading: 'Account unavailable',
      body: "This account isn't currently active.",
      cta: 'Back to home',
      href: '/',
    },
    {
      reason: 'state_invalid',
      heading: 'Sign-in expired',
      body: 'Your sign-in link expired.',
      cta: 'Try sign-in again',
      href: '/api/auth/login/',
    },
    {
      reason: 'code_exchange_failed',
      heading: 'Sign-in failed',
      body: "We couldn't complete sign-in.",
      cta: 'Try sign-in again',
      href: '/api/auth/login/',
    },
  ] as const;

  for (const { reason, heading, body, cta, href } of cases) {
    it(`renders the ${reason} code with the right heading, body, and CTA`, () => {
      setReason(reason);
      render(Page);

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(heading);
      expect(screen.getByText(body)).toBeInTheDocument();
      const link = screen.getByRole('link', { name: cta });
      expect(link).toHaveAttribute('href', href);
    });
  }

  it('falls through to the generic copy when reason is missing', () => {
    setReason(null);
    render(Page);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Something went wrong');
    expect(screen.getByText('An unexpected error occurred during sign-in.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to home' })).toHaveAttribute('href', '/');
  });

  it('falls through to the generic copy when reason is unrecognized', () => {
    setReason('not_a_real_code');
    render(Page);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Something went wrong');
  });

  it('marks all retryable CTAs with data-sveltekit-reload so the router does not intercept', () => {
    // /api/auth/login/ is a Django endpoint; client-side navigation would
    // 404 in the router. Verify the reload hint is present on the retry CTA.
    setReason('state_invalid');
    render(Page);
    const link = screen.getByRole('link', { name: 'Try sign-in again' });
    expect(link).toHaveAttribute('data-sveltekit-reload');
  });
});
