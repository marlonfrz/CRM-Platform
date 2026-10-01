import { formatUtcTimestamp } from "@/lib/date-time";
import type { SummaryLatest } from "@/lib/summaries";
import { SummarySectionCard } from "./SummarySectionCard";
import styles from "./LatestSummaries.module.css";

export function LatestSummaries({ items, loading, error }: {
  items: SummaryLatest[]; loading: boolean; error: string;
}) {
  return <section className={styles.list} aria-label="Últimos resúmenes guardados">
    <h2>Últimos resúmenes guardados</h2>
    {loading ? <p role="status">Cargando resúmenes guardados…</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {!loading && !error && !items.length ? <p>Aún no hay resúmenes guardados para este alcance.</p> : null}
    {!loading && !error ? items.map((item) => <div className={styles.entry}
      key={`${item.section.department_id ?? "personal"}:${item.generated_at}`}>
      <div className={styles.meta}>
        <span>Generado: <strong>{formatUtcTimestamp(item.generated_at)}</strong></span>
        <span>Periodo: {formatUtcTimestamp(item.since)} – {formatUtcTimestamp(item.until)}</span>
        <span>{item.provider} · {item.model}</span>
      </div>
      <SummarySectionCard section={item.section} />
    </div>) : null}
  </section>;
}
