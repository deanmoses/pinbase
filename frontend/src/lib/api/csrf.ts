export function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match?.[1];
}
