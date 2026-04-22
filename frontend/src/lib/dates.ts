/** Friendly date formatting utilities. */

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function formatTime(date: Date): string {
  const minutes = date.getMinutes();
  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: minutes === 0 ? undefined : '2-digit',
  });
  return formatter.format(date).toLowerCase();
}

export function smartDate(iso: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const calendarDays = Math.round((startOfToday.getTime() - startOfDate.getTime()) / 86_400_000);

  if (isSameDay(date, now)) {
    return formatTime(date);
  }

  if (calendarDays === 1) {
    const yesterday = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(-1, 'day');
    return `${yesterday[0].toUpperCase()}${yesterday.slice(1)} ${formatTime(date)}`;
  }

  if (calendarDays > 0 && calendarDays < 7) {
    const weekday = new Intl.DateTimeFormat(undefined, { weekday: 'long' }).format(date);
    return `${weekday} ${formatTime(date)}`;
  }

  if (date.getFullYear() === now.getFullYear()) {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
    }).format(date);
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

export function fullDateTime(iso: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

export function formatDate(iso: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date);
}
