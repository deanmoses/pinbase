import client from '$lib/api/client';

interface AuthState {
	isAuthenticated: boolean;
	id: number | null;
	username: string | null;
}

function createAuthStore() {
	let state = $state<AuthState>({
		isAuthenticated: false,
		id: null,
		username: null
	});
	let loaded = $state(false);

	async function load() {
		if (loaded) return;
		const { data } = await client.GET('/api/auth/me/');
		if (data) {
			state = {
				isAuthenticated: data.is_authenticated,
				id: data.id ?? null,
				username: data.username ?? null
			};
		}
		loaded = true;
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
		get loaded() {
			return loaded;
		},
		load
	};
}

export const auth = createAuthStore();
