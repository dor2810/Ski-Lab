export function formatEUR(value: number, locale: string = "en-GB"): string {
  return `€${Math.round(value).toLocaleString(locale)}`;
}

export function formatDate(iso: string, locale: string = "en-GB"): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(locale, { day: "numeric", month: "short" });
}

export function todayPlusDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
