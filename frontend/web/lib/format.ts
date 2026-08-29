export function formatEUR(value: number, locale: string = "en-GB"): string {
  return `€${Math.round(value).toLocaleString(locale)}`;
}

export function formatDate(iso: string, locale: string = "en-GB"): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(locale, { day: "numeric", month: "short" });
}

// Chip label for the price-by-start-date switcher: weekday + date,
// e.g. "Sat 5 Dec" / "שבת 5 בדצמ׳" -- the weekday is load-bearing on a
// ski card (Saturday is the classic changeover day).
export function formatShortDate(iso: string, locale: string = "en-GB"): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" });
}

// Short weekday label for a single day in a weather breakdown, e.g.
// "Sun" / "יום א׳" depending on locale.
export function formatWeekday(iso: string, locale: string = "en-GB"): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(locale, { weekday: "short" });
}

// Formats a Date's LOCAL calendar date as YYYY-MM-DD. Deliberately not
// `d.toISOString().slice(0, 10)` -- toISOString converts to UTC first,
// which silently shifts the date back a day for anyone in a timezone
// ahead of UTC (e.g. Israel, this app's actual target market) once the
// local time is past midnight but before the UTC offset catches up.
function toLocalISODate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayPlusDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return toLocalISODate(d);
}

export function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + days);
  return toLocalISODate(d);
}
