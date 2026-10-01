import type { SummaryResult } from "@/lib/summaries";
import { SummarySourceItem } from "./SummarySourceItem";
import styles from "./SummarySectionCard.module.css";

type Section = SummaryResult["sections"][number];

export function SummarySectionCard({ section }: { section: Section }) {
  return <article className={styles.section}>
    <h2>{section.department_name ?? "Resumen personal"}</h2>
    <p className={styles.content}>{section.content.summary}</p>
    {section.content.pending_actions.length ? <>
      <h3>Próximas acciones mencionadas</h3>
      <ul>{section.content.pending_actions.map((item, index) => <li key={index}>{item}</li>)}</ul>
    </> : null}
    <details><summary>Actividades utilizadas ({section.sources.length})</summary>
      <ul className={styles.sources}>{section.sources.map((source) =>
        <SummarySourceItem key={source.id} source={source}
          cited={section.content.source_ids.includes(source.id)} />)}</ul>
    </details>
  </article>;
}
