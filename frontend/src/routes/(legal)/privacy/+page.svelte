<script lang="ts">
  import { SITE_NAME, pageTitle } from '$lib/constants';
</script>

<svelte:head>
  <title>{pageTitle('Privacy Policy')}</title>
</svelte:head>

<h1>Privacy Policy</h1>
<p class="last-updated">Last updated: March 2026</p>

<h2>Information We Collect</h2>
<p>
  {SITE_NAME} collects minimal information needed to operate the service:
</p>
<ul>
  <li>
    <strong>Account information</strong> — email address and display name, if you create an account.
  </li>
  <li>
    <strong>Usage data</strong> — standard web server logs including IP addresses, browser type, and pages
    visited.
  </li>
</ul>

<h2>How We Use Information</h2>
<p>
  We use collected information to operate and improve the service. We do not sell personal
  information to third parties.
</p>

<h2>Cookies</h2>
<p>
  {SITE_NAME} uses a small number of cookies for essential functionality:
</p>
<ul>
  <li><strong>Session cookie</strong> — maintains your login state.</li>
  <li><strong>CSRF token</strong> — protects against cross-site request forgery.</li>
</ul>
<p>We do not use tracking or advertising cookies.</p>

<h2>Data Retention</h2>
<p>
  Account information is retained while your account is active. Server logs are retained for a
  limited period for operational purposes. You may request deletion of your account and associated
  data at any time.
</p>
<!-- TODO: Add account deletion process details -->

<h2>Third-Party Services</h2>
<p>
  {SITE_NAME} is hosted on <a href="https://railway.com" target="_blank" rel="noopener">Railway</a>.
  Your interactions with the service are subject to Railway's infrastructure and data handling
  practices.
</p>
<!-- TODO: Add any analytics services if applicable -->

<h2>Your Rights</h2>
<p>
  You have the right to access, correct, or delete your personal information. To exercise these
  rights, please
  <!-- TODO: Add contact method -->
  contact us.
</p>

<h2>Changes to This Policy</h2>
<p>
  We may update this policy from time to time. Changes will be posted on this page with an updated
  date.
</p>

<h2>Contact</h2>
<p>
  If you have questions about this privacy policy, please
  <!-- TODO: Add contact method -->
  contact us.
</p>
