import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { goto, resolve, GET, PATCH, DELETE, POST } = vi.hoisted(() => ({
  goto: vi.fn(),
  resolve: vi.fn((url: string) => url),
  GET: vi.fn(),
  PATCH: vi.fn(),
  DELETE: vi.fn(),
  POST: vi.fn(),
}));

vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/paths', () => ({ resolve }));
vi.mock('$lib/api/client', () => ({ default: { GET, PATCH, DELETE, POST } }));

import Page from './+page.svelte';
import { clearKioskCookies, setKioskCookies } from '$lib/kiosk/config';
import { toast } from '$lib/toast/toast.svelte';

function makeData(
  overrides: Partial<{ id: number; page_heading: string; idle_seconds: number }> = {},
) {
  return {
    config: {
      id: 7,
      page_heading: '',
      idle_seconds: 60,
      items: [],
      ...overrides,
    },
  };
}

describe('/kiosk/edit/[id] editor — delete handler', () => {
  beforeEach(() => {
    goto.mockReset().mockResolvedValue(undefined);
    GET.mockReset().mockResolvedValue({ data: [] });
    PATCH.mockReset();
    DELETE.mockReset();
    clearKioskCookies();
    toast._resetForTest();
  });

  afterEach(() => {
    toast._resetForTest();
  });

  it('cancelled confirm: no DELETE, no goto, cookies untouched', async () => {
    const user = userEvent.setup();
    setKioskCookies(7, 60);
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    render(Page, { data: makeData() });
    await user.click(screen.getAllByRole('button', { name: 'Delete Kiosk' })[0]);

    expect(confirmSpy).toHaveBeenCalled();
    expect(DELETE).not.toHaveBeenCalled();
    expect(goto).not.toHaveBeenCalled();
    expect(document.cookie).toContain('mode=kiosk');
    expect(document.cookie).toContain('kioskConfigId=7');
    confirmSpy.mockRestore();
  });

  it('confirmed, non-active config: DELETE called, goto fires, cookies untouched', async () => {
    const user = userEvent.setup();
    setKioskCookies(99, 60); // active is a DIFFERENT kiosk
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    DELETE.mockResolvedValue({ response: { status: 204 }, error: undefined });

    render(Page, { data: makeData() });
    await user.click(screen.getAllByRole('button', { name: 'Delete Kiosk' })[0]);

    await waitFor(() => expect(DELETE).toHaveBeenCalledTimes(1));
    expect(DELETE).toHaveBeenCalledWith('/api/kiosk/configs/{config_id}/', {
      params: { path: { config_id: 7 } },
    });
    expect(goto).toHaveBeenCalledWith('/kiosk/edit');
    // Other-kiosk cookie left intact.
    expect(document.cookie).toContain('kioskConfigId=99');
    confirmSpy.mockRestore();
  });

  it('confirmed, active config: cookies cleared BEFORE DELETE call', async () => {
    const user = userEvent.setup();
    setKioskCookies(7, 60); // active matches
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    let cookieAtDeleteTime: string | null = null;
    DELETE.mockImplementation(async () => {
      cookieAtDeleteTime = document.cookie;
      return { response: { status: 204 }, error: undefined };
    });

    render(Page, { data: makeData() });
    await user.click(screen.getAllByRole('button', { name: 'Delete Kiosk' })[0]);

    await waitFor(() => expect(DELETE).toHaveBeenCalled());
    expect(cookieAtDeleteTime).not.toContain('kioskConfigId=7');
    expect(cookieAtDeleteTime).not.toContain('mode=kiosk');
    expect(goto).toHaveBeenCalledWith('/kiosk/edit');
    confirmSpy.mockRestore();
  });

  it('DELETE failure: no goto, error message rendered', async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    DELETE.mockResolvedValue({ response: { status: 500 }, error: { detail: 'boom' } });

    render(Page, { data: makeData() });
    await user.click(screen.getAllByRole('button', { name: 'Delete Kiosk' })[0]);

    await waitFor(() => expect(DELETE).toHaveBeenCalled());
    expect(goto).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    confirmSpy.mockRestore();
  });
});

describe('/kiosk/edit/[id] editor — autosave on blur', () => {
  beforeEach(() => {
    goto.mockReset().mockResolvedValue(undefined);
    GET.mockReset().mockResolvedValue({ data: [] });
    PATCH.mockReset();
    clearKioskCookies();
    toast._resetForTest();
  });

  it('blurring page-heading PATCHes the current state', async () => {
    const user = userEvent.setup();
    PATCH.mockResolvedValue({
      data: { id: 7, page_heading: 'Welcome', idle_seconds: 60, items: [] },
      error: undefined,
    });

    render(Page, { data: makeData() });
    const headingInput = screen.getByLabelText(/Front door heading/i);
    await user.clear(headingInput);
    await user.type(headingInput, 'Welcome');
    await user.tab(); // blur

    await waitFor(() => expect(PATCH).toHaveBeenCalled());
    expect(PATCH).toHaveBeenCalledWith(
      '/api/kiosk/configs/{config_id}/',
      expect.objectContaining({
        body: expect.objectContaining({ page_heading: 'Welcome' }),
      }),
    );
  });

  it('coalesces overlapping saves: a blur during an in-flight save fires exactly one trailing PATCH', async () => {
    const user = userEvent.setup();
    // Hold the first PATCH until we explicitly resolve it so the second
    // blur lands while the first is still in flight.
    let resolveFirst!: (v: unknown) => void;
    const firstPromise = new Promise((r) => {
      resolveFirst = r;
    });
    PATCH.mockImplementationOnce(() => firstPromise).mockResolvedValue({
      data: { id: 7, page_heading: 'H', idle_seconds: 90, items: [] },
      error: undefined,
    });

    render(Page, { data: makeData() });
    const headingInput = screen.getByLabelText(/Front door heading/i);
    const idleInput = screen.getByLabelText(/Idle timeout/i);

    await user.clear(headingInput);
    await user.type(headingInput, 'H');
    await user.tab(); // blur heading → first save starts and hangs
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1));

    // While the first is still pending, edit + blur a second field.
    await user.clear(idleInput);
    await user.type(idleInput, '90');
    await user.tab();
    // No second PATCH yet — coalescer should be holding it.
    expect(PATCH).toHaveBeenCalledTimes(1);

    // Resolve the first save. The trailing save should fire with the
    // current state (both fields).
    resolveFirst({
      data: { id: 7, page_heading: 'H', idle_seconds: 60, items: [] },
      error: undefined,
    });
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(2));
    expect(PATCH).toHaveBeenLastCalledWith(
      '/api/kiosk/configs/{config_id}/',
      expect.objectContaining({
        body: expect.objectContaining({ page_heading: 'H', idle_seconds: 90 }),
      }),
    );
  });

  it('blurring idle-seconds refreshes the kioskIdleSeconds cookie when this device is active', async () => {
    const user = userEvent.setup();
    setKioskCookies(7, 60);
    PATCH.mockResolvedValue({
      data: { id: 7, page_heading: '', idle_seconds: 120, items: [] },
      error: undefined,
    });

    render(Page, { data: makeData() });
    const idleInput = screen.getByLabelText(/Idle timeout/i);
    await user.clear(idleInput);
    await user.type(idleInput, '120');
    await user.tab(); // blur

    await waitFor(() => expect(PATCH).toHaveBeenCalled());
    await waitFor(() => expect(document.cookie).toContain('kioskIdleSeconds=120'));
  });
});
