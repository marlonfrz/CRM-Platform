export function defaultSummaryPeriod(now = new Date()) {
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth();
  const day = now.getUTCDate();
  const lastDayNextMonth = new Date(Date.UTC(year, month + 2, 0)).getUTCDate();
  const since = new Date(Date.UTC(year, month, day));
  const until = new Date(Date.UTC(year, month + 1, Math.min(day, lastDayNextMonth), 23, 59));
  return {
    since: since.toISOString().slice(0, 16),
    until: until.toISOString().slice(0, 16),
  };
}
