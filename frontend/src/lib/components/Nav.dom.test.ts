// Responsive bar layout (desktop vs tablet vs mobile) is verified visually,
// not in JSDOM — these tests cover the menu contents per auth state.
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { pageState, auth } = vi.hoisted(() => ({
  pageState: {
    url: new URL('http://localhost:5173/'),
    params: {} as Record<string, string>,
  },
  auth: {
    isAuthenticated: false,
    isSuperuser: false,
    username: null as string | null,
    firstName: '',
    lastName: '',
    loaded: true,
    load: () => Promise.resolve(),
    logout: vi.fn(() => Promise.resolve()),
  },
}));

vi.mock('$app/state', () => ({ page: pageState }));
vi.mock('$app/paths', () => ({ resolve: (p: string) => p }));
vi.mock('$lib/auth.svelte', () => ({ auth }));

import Nav from './Nav.svelte';

function setAuth(overrides: Partial<typeof auth>) {
  Object.assign(auth, {
    isAuthenticated: false,
    isSuperuser: false,
    username: null,
    firstName: '',
    lastName: '',
    loaded: true,
    logout: vi.fn(() => Promise.resolve()),
  });
  Object.assign(auth, overrides);
}

describe('Nav', () => {
  beforeEach(() => {
    pageState.url = new URL('http://localhost:5173/');
  });

  it('anonymous: renders Sign in link, no avatar, no admin items', async () => {
    const user = userEvent.setup();
    setAuth({});
    render(Nav);

    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.queryByTestId('avatar')).not.toBeInTheDocument();

    // Open the hamburger and confirm there's no admin section.
    await user.click(screen.getByRole('button', { name: 'Menu' }));
    expect(screen.queryByText('admin')).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: 'Django Admin' })).not.toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('authed non-superuser: avatar with initials, menu has My Contributions + Sign Out, no admin', async () => {
    const user = userEvent.setup();
    setAuth({
      isAuthenticated: true,
      username: 'alice',
      firstName: 'Alice',
      lastName: 'Anderson',
    });
    render(Nav);

    expect(screen.getByTestId('avatar')).toHaveTextContent('AA');

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    expect(screen.getByRole('menuitem', { name: 'My Contributions' })).toHaveAttribute(
      'href',
      '/users/alice',
    );
    expect(screen.getByRole('menuitem', { name: 'Sign Out' })).toBeInTheDocument();
    expect(screen.queryByText('admin')).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: 'Django Admin' })).not.toBeInTheDocument();
  });

  it('authed superuser: account menu shows admin section with Kiosk Config and Django Admin', async () => {
    const user = userEvent.setup();
    setAuth({
      isAuthenticated: true,
      isSuperuser: true,
      username: 'root',
      firstName: 'Root',
      lastName: 'User',
    });
    render(Nav);

    await user.click(screen.getByRole('button', { name: 'Account menu' }));

    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Kiosk Config' })).toHaveAttribute(
      'href',
      '/kiosk/configure',
    );
    expect(screen.getByRole('menuitem', { name: 'Django Admin' })).toHaveAttribute(
      'href',
      '/admin/',
    );
  });

  it('Sign Out menu item calls auth.logout()', async () => {
    const user = userEvent.setup();
    setAuth({
      isAuthenticated: true,
      username: 'alice',
      firstName: 'Alice',
      lastName: 'Anderson',
    });
    render(Nav);

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.click(screen.getByRole('menuitem', { name: 'Sign Out' }));

    expect(auth.logout).toHaveBeenCalledTimes(1);
  });
});
