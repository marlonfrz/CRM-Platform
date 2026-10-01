import { MutedText } from "@/components/ui/Text";
import { formatUtcTimestamp } from "@/lib/date-time";
import { type SummaryResult as Result } from "@/lib/summaries";
import { SummaryCostCard } from "./SummaryCostCard";
import { SummarySectionCard } from "./SummarySectionCard";
import styles from "./SummaryResult.module.css";

export function SummaryResult({ result, period }: {
  result: Result; period?: { since: string; until: string } | null;
}) {
  return <section className={styles.results} aria-label="Resultado del resumen">
    <MutedText>{result.cached ? "Resultado reutilizado" : "Generado"}: {formatUtcTimestamp(result.generated_at)} · {result.provider} / {result.model}</MutedText>
    {period ? <MutedText>Periodo: {formatUtcTimestamp(period.since)} – {formatUtcTimestamp(period.until)}</MutedText> : null}
    <SummaryCostCard result={result} />
    <MutedText>Revisa las fuentes: la IA puede equivocarse. Las próximas acciones sugeridas no son tareas creadas ni confirmadas.</MutedText>
    {!result.sections.length ? <p>No hay actividades autorizadas en este periodo. No se ha consultado la IA.</p> : null}
    {result.sections.map((section) => <SummarySectionCard
      key={section.department_id ?? "personal"} section={section} />)}
  </section>;
}
