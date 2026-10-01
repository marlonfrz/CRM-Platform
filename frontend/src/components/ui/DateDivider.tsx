import styles from "./DateDivider.module.css";

export function DateDivider({ date, id }: { date: string; id?: string }) {
  const label = new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T12:00:00Z`));

  return <h3 className={styles.divider} id={id}>
    <time dateTime={date}>{label}</time>
  </h3>;
}
