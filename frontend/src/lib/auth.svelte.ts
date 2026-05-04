import client from '$lib/api/client';

interface AuthState {
  isAuthenticated: boolean;
  id: number | null;
  username: string | null;
  isSuperuser: boolean;
  firstName: string;
  lastName: string;
}

const ANONYMOUS: AuthState = {
  isAuthenticated: false,
  id: null,
  username: null,
  isSuperuser: false,
  firstName: '',
  lastName: '',
};

function createAuthStore() {
  let state = $state<AuthState>({ ...ANONYMOUS });
  let loaded = $state(false);

  function set(data: {
    is_authenticated: boolean;
    id?: number | null;
    username?: string | null;
    is_superuser?: boolean;
    first_name?: string;
    last_name?: string;
  }) {
    state = {
      isAuthenticated: data.is_authenticated,
      id: data.id ?? null,
      username: data.username ?? null,
      isSuperuser: data.is_superuser ?? false,
      firstName: data.first_name ?? '',
      lastName: data.last_name ?? '',
    };
    loaded = true;
  }

  async function load() {
    if (loaded) return;
    const { data } = await client.GET('/api/auth/me/');
    if (data) set(data);
  }

  async function logout() {
    const { data } = await client.POST('/api/auth/logout/');
    if (data) set({ is_authenticated: false });
  }

  return {
    get isAuthenticated() {
      return state.isAuthenticated;
    },
    get id() {
      return state.id;
    },
    get username() {
      return state.username;
    },
    get isSuperuser() {
      return state.isSuperuser;
    },
    get firstName() {
      return state.firstName;
    },
    get lastName() {
      return state.lastName;
    },
    get loaded() {
      return loaded;
    },
    load,
    logout,
  };
}

export const auth = createAuthStore();
