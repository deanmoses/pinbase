import { onMount } from 'svelte';

/**
 * Reactive async data loader for use inside Svelte components.
 *
 * Fetches data in `onMount` and exposes reactive `data`, `loading`,
 * and `error` properties via getters.
 */
export function createAsyncLoader<T>(fetcher: () => Promise<T>, initial: NoInfer<T>) {
	let data = $state(initial);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			data = await fetcher();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load data';
		} finally {
			loading = false;
		}
	});

	return {
		get data() {
			return data;
		},
		get loading() {
			return loading;
		},
		get error() {
			return error;
		}
	};
}
