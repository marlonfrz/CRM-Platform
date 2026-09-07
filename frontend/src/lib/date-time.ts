export function formatUtcTimestamp(value: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
  }).format(new Date(value)) + " UTC";
}
