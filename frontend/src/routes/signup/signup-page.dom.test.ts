import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const GET = vi.fn();
const POST = vi.fn();

vi.mock('$lib/api/client', () => ({
  default: { GET, POST },
}));

// Import after mock so the page closes over the mocked client.
const Page = (await import('./+page.svelte')).default;

function makeResponse(status: number): Response {
  return new Response(null, { status });
}

const pending = {
  first_name: 'Alice',
  last_name: 'Anderson',
  email: 'alice@example.com',
};

const originalLocation = window.location;

beforeEach(() => {
  GET.mockReset();
  POST.mockReset();
  // jsdom forbids real navigation; replace location with a writable stub so
  // assignments to href are observable instead of throwing.
  Object.defineProperty(window, 'location', {
    configurable: true,
    writable: true,
    value: { href: '' },
  });
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    writable: true,
    value: originalLocation,
  });
});

describe('signup page — header', () => {
  it('renders the user identity bar', () => {
    render(Page, { props: { data: { pending } } });
    expect(screen.getByText(/Continuing as/i)).toBeInTheDocument();
    expect(screen.getByText('Alice Anderson')).toBeInTheDocument();
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /not you/i })).toBeInTheDocument();
  });
});

describe('signup page — local format reject (no network call)', () => {
  it('stays silent below USERNAME_MIN_LEN (no message, no /check call)', async () => {
    // too_short while the user is still typing is hostile; the server
    // surfaces it on submit instead. Pre-check + /check both suppressed.
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'ab' } });
    expect(screen.queryByText(/at least 3 characters/i)).not.toBeInTheDocument();
    expect(GET).not.toHaveBeenCalled();
  });

  it('shows too_short copy if the server rejects on submit', async () => {
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'ab' } });

    POST.mockResolvedValue({
      data: undefined,
      response: new Response(
        JSON.stringify({
          detail: { kind: 'username_rejected', message: 'rejected', reason: 'too_short' },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    });

    // The Continue button is disabled when status !== 'available'; force-submit
    // the form to simulate a user finding their way around (e.g. Enter key).
    const form = input.closest('form')!;
    await fireEvent.submit(form);
    await waitFor(() => expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument());
  });

  it('shows bad-charset copy for uppercase (after lowercase normalization, still invalid for underscore)', async () => {
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'al_ice' } });
    expect(
      await screen.findByText(/only lowercase letters, numbers, and hyphens/i),
    ).toBeInTheDocument();
    expect(GET).not.toHaveBeenCalled();
  });

  it('lowercases input as the user types', async () => {
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'AliCE' } });
    expect(input.value).toBe('alice');
  });
});

describe('signup page — debounced /check', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('reports Available on a successful check', async () => {
    GET.mockResolvedValue({
      data: { available: true, reason: null },
      response: makeResponse(200),
    });
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'alice' } });

    await vi.advanceTimersByTimeAsync(300);
    await waitFor(() => expect(screen.getByText('Available')).toBeInTheDocument());
    expect(GET).toHaveBeenCalledWith('/api/auth/signup/check/', {
      params: { query: { username: 'alice' } },
    });
  });

  it('reports Not available when /check returns taken', async () => {
    GET.mockResolvedValue({
      data: { available: false, reason: 'taken' },
      response: makeResponse(200),
    });
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'alice' } });

    await vi.advanceTimersByTimeAsync(300);
    await waitFor(() => expect(screen.getByText('Not available')).toBeInTheDocument());
  });

  it('shows reserved copy when /check returns reserved', async () => {
    GET.mockResolvedValue({
      data: { available: false, reason: 'reserved' },
      response: makeResponse(200),
    });
    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'admin' } });

    await vi.advanceTimersByTimeAsync(300);
    await waitFor(() => expect(screen.getByText('Not available.')).toBeInTheDocument());
  });

  it('discards a stale /check response when the input drops below MIN_LEN mid-flight', async () => {
    // Regression: type "alice" (kicks off a check), then shorten to "al"
    // before the response lands. The stale "available" response must NOT
    // promote the now-invalid input to status=available.
    let resolveCheck!: (value: {
      data: { available: boolean; reason: string | null };
      response: Response;
    }) => void;
    GET.mockImplementation(
      () =>
        new Promise((r) => {
          resolveCheck = r;
        }),
    );

    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'alice' } });
    await vi.advanceTimersByTimeAsync(300); // setTimeout fires, GET in flight

    // User shortens before the GET resolves.
    await fireEvent.input(input, { target: { value: 'al' } });

    // Stale response arrives.
    resolveCheck({
      data: { available: true, reason: null },
      response: makeResponse(200),
    });
    await vi.advanceTimersByTimeAsync(0); // flush microtasks

    expect(screen.queryByText('Available')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
  });

  it('discards a stale /check response when input becomes format-invalid mid-flight', async () => {
    // Same shape as above but for the format-reject early-return path.
    let resolveCheck!: (value: {
      data: { available: boolean; reason: string | null };
      response: Response;
    }) => void;
    GET.mockImplementation(
      () =>
        new Promise((r) => {
          resolveCheck = r;
        }),
    );

    render(Page, { props: { data: { pending } } });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value: 'alice' } });
    await vi.advanceTimersByTimeAsync(300);

    // User pastes an underscore in the middle — invalid charset.
    await fireEvent.input(input, { target: { value: 'al_ice' } });

    resolveCheck({
      data: { available: true, reason: null },
      response: makeResponse(200),
    });
    await vi.advanceTimersByTimeAsync(0);

    expect(screen.queryByText('Available')).not.toBeInTheDocument();
    expect(screen.getByText(/only lowercase letters, numbers, and hyphens/i)).toBeInTheDocument();
  });
});

describe('signup page — submit', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  async function makeAvailable(value: string) {
    GET.mockResolvedValue({
      data: { available: true, reason: null },
      response: makeResponse(200),
    });
    const input = screen.getByPlaceholderText('your-username');
    await fireEvent.input(input, { target: { value } });
    await vi.advanceTimersByTimeAsync(300);
    await waitFor(() => expect(screen.getByText('Available')).toBeInTheDocument());
  }

  it('navigates to redirect_url on success', async () => {
    render(Page, { props: { data: { pending } } });
    await makeAvailable('alice');

    POST.mockResolvedValue({
      data: { redirect_url: '/dashboard' },
      response: makeResponse(200),
    });

    const submitBtn = screen.getByRole('button', { name: /continue/i });
    await fireEvent.click(submitBtn);

    await waitFor(() => expect(window.location.href).toBe('/dashboard'));
    expect(POST).toHaveBeenCalledWith('/api/auth/signup/', {
      body: { username: 'alice' },
    });
  });

  it('shows the taken copy when server returns username_taken (race after available)', async () => {
    render(Page, { props: { data: { pending } } });
    await makeAvailable('alice');

    POST.mockResolvedValue({
      data: undefined,
      response: new Response(
        JSON.stringify({ detail: { kind: 'username_taken', message: 'Username is taken.' } }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    });

    const submitBtn = screen.getByRole('button', { name: /continue/i });
    await fireEvent.click(submitBtn);

    await waitFor(() => expect(screen.getByText('Not available')).toBeInTheDocument());
    expect(window.location.href).toBe('');
  });

  it('updates status when server returns username_rejected with a reason', async () => {
    render(Page, { props: { data: { pending } } });
    await makeAvailable('alice');

    POST.mockResolvedValue({
      data: undefined,
      response: new Response(
        JSON.stringify({
          detail: { kind: 'username_rejected', message: 'rejected', reason: 'reserved' },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    });

    const submitBtn = screen.getByRole('button', { name: /continue/i });
    await fireEvent.click(submitBtn);

    await waitFor(() => expect(screen.getByText('Not available.')).toBeInTheDocument());
  });
});

describe('signup page — cancel', () => {
  it('navigates to logout_url returned by the cancel endpoint', async () => {
    POST.mockResolvedValue({
      data: { logout_url: 'https://idp.example.com/logout?return_to=/' },
      response: makeResponse(200),
    });
    render(Page, { props: { data: { pending } } });

    const notYou = screen.getByRole('button', { name: /not you/i });
    await fireEvent.click(notYou);

    await waitFor(() =>
      expect(window.location.href).toBe('https://idp.example.com/logout?return_to=/'),
    );
    expect(POST).toHaveBeenCalledWith('/api/auth/signup/cancel/', {});
  });

  it('falls back to / on error', async () => {
    POST.mockRejectedValue(new Error('network'));
    render(Page, { props: { data: { pending } } });

    const notYou = screen.getByRole('button', { name: /not you/i });
    await fireEvent.click(notYou);

    await waitFor(() => expect(window.location.href).toBe('/'));
  });
});
