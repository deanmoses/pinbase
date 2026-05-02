import { SITE_TITLE } from '$lib/constants';

const MAX_DESC_LENGTH = 155;

export function buildFullTitle(title: string): string {
  return title === SITE_TITLE ? SITE_TITLE : `${title} — ${SITE_TITLE}`;
}

export function truncateDescription(description: string): string {
  return description.length > MAX_DESC_LENGTH
    ? description.slice(0, MAX_DESC_LENGTH - 1) + '\u2026'
    : description;
}

export function buildCanonicalUrl(url: string): string {
  return url.split('?')[0].split('#')[0];
}

export function twitterCardType(image: string | null | undefined): string {
  return image ? 'summary_large_image' : 'summary';
}
