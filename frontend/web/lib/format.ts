export function formatEUR(value: number): string {
  return `€${Math.round(value).toLocaleString("en-US")}`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function seasonLabel(season?: string): string {
  if (season === "peak") return "Peak";
  if (season === "high") return "High";
  if (season === "shoulder") return "Shoulder";
  return "";
}

export function todayPlusDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
