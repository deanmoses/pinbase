<script>
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>Home</title>
</svelte:head>

<h1>Welcome</h1>
<p>Public landing page (prerendered).</p>
<p><a href={resolve('/dashboard')}>Go to dashboard</a></p>
