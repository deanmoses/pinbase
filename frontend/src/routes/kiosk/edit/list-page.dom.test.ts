import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { goto, resolve, POST } = vi.hoisted(() => ({
  goto: vi.fn(),
  resolve: vi.fn((url: string) => url),
  POST: vi.fn(),
}));

vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/paths', () => ({ resolve }));
vi.mock('$lib/api/client', () => ({ default: { POST } }));

import Page from './+page.svelte';
import { clearKioskCookies, setKioskCookies } from '$lib/kiosk/config';
import { toast } from '$lib/toast/toast.svelte';

function makeData(
  configs: {
    id: number;
    page_heading: string;
    idle_seconds: number;
    item_count: number;
  }[],
  activeId: number | null = null,
) {
  return { configs, activeId };
}

describe('/kiosk/edit list page', () => {
  beforeEach(() => {
    goto.mockReset().mockResolvedValue(undefined);
    POST.mockReset();
    clearKioskCookies();
    toast._resetForTest();
  });

  it('shows the empty state when there are no configs', () => {
    render(Page, { data: makeData([]) });
    expect(screen.getByText(/No kiosks yet/i)).toBeInTheDocument();
  });

  it('renders rows as "#id" when no page heading, "#id - heading" otherwise', () => {
    render(Page, {
      data: makeData([
        { id: 1, page_heading: '', idle_seconds: 60, item_count: 3 },
        { id: 2, page_heading: 'Welcome', idle_seconds: 90, item_count: 1 },
      ]),
    });
    expect(screen.getByText('Kiosk #1')).toBeInTheDocument();
    expect(screen.getByText('Kiosk #2 - Welcome')).toBeInTheDocument();
  });

  it('shows the "Active on this device" pill on the row matching activeId', () => {
    render(Page, {
      data: makeData(
        [
          { id: 1, page_heading: '', idle_seconds: 60, item_count: 3 },
          { id: 2, page_heading: '', idle_seconds: 90, item_count: 1 },
        ],
        2,
      ),
    });
    expect(screen.getByText('Active on this device')).toBeInTheDocument();
    // Active row shows Exit; the other shows Enter.
    expect(screen.getByRole('button', { name: 'Exit Kiosk Mode' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enter Kiosk Mode' })).toBeInTheDocument();
  });

  it('clicking Exit Kiosk Mode clears cookies and removes the pill', async () => {
    const user = userEvent.setup();
    setKioskCookies(2, 90);
    render(Page, {
      data: makeData([{ id: 2, page_heading: '', idle_seconds: 90, item_count: 1 }], 2),
    });

    expect(screen.getByText('Active on this device')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Exit Kiosk Mode' }));

    expect(screen.queryByText('Active on this device')).not.toBeInTheDocument();
    expect(document.cookie).not.toContain('mode=kiosk');
  });

  it('"+ New Kiosk" POSTs and navigates on success', async () => {
    const user = userEvent.setup();
    POST.mockResolvedValue({ data: { id: 42 }, error: undefined });
    render(Page, { data: makeData([]) });

    await user.click(screen.getAllByRole('button', { name: '+ New Kiosk' })[0]);

    expect(POST).toHaveBeenCalledWith('/api/kiosk/configs/');
    await waitFor(() => expect(goto).toHaveBeenCalledWith('/kiosk/edit/42'));
    expect(toast.messages.map((m) => m.text)).toContain('Created kiosk #42.');
  });

  it('"+ New Kiosk" surfaces an inline error when POST fails', async () => {
    const user = userEvent.setup();
    POST.mockResolvedValue({ data: undefined, error: { detail: 'boom' } });
    render(Page, { data: makeData([]) });

    await user.click(screen.getAllByRole('button', { name: '+ New Kiosk' })[0]);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(goto).not.toHaveBeenCalled();
  });
});
