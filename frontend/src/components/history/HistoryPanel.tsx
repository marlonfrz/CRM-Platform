import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { HistoryFilters, HistoryPage, historyPageQuery } from "@/lib/insights";
import { HistoryItem } from "./HistoryItem";
import styles from "./HistoryPanel.module.css";

export function HistoryPanel({ clientId, page, filters, preservedQuery = "" }: {
  clientId: string; page: HistoryPage; filters: HistoryFilters; preservedQuery?: string;
}) {
  const path = `/clients/${clientId}`;
  return <Card className={styles.card} id="history" aria-label="Historial del cliente">
    <header className={styles.header}><h2>Historial del cliente</h2>
      <MutedText>Actividades y tareas que puedes consultar, de más reciente a más antiguo.</MutedText>
      <MutedText>Las tareas muestran su estado actual: se ordenan por finalización o, si siguen pendientes, por creación. No es un registro de cada cambio.</MutedText>
    </header>
    <form action={`${path}#history`} method="get" className={styles.filters} key={filters.kind}>
      {Array.from(new URLSearchParams(preservedQuery)).map(([key, value]) => <input key={key} type="hidden" name={key} value={value} />)}
      <SelectField label="Mostrar" name="history_kind" defaultValue={filters.kind} options={[
        { value: "", label: "Actividades y tareas" }, { value: "ACTIVITY", label: "Solo actividades" }, { value: "TASK", label: "Solo tareas" },
      ]} />
      <Button type="submit" variant="quiet">Filtrar historial</Button>
    </form>
    <div className={styles.list}>
      {page.items.map((entry) => <HistoryItem key={`${entry.kind}:${entry.id}`} entry={entry} />)}
      {!page.items.length ? <MutedText className={styles.empty}>No hay registros visibles con este filtro.</MutedText> : null}
    </div>
    {page.has_more || filters.offset > 0 ? <nav className={styles.pagination} aria-label="Páginas del historial">
      {filters.offset > 0 ? <Link href={`${path}?${historyPageQuery({ ...filters, offset: Math.max(0, filters.offset - 20) }, preservedQuery)}#history`}>← Anteriores</Link> : <span />}
      {page.has_more ? <Link href={`${path}?${historyPageQuery({ ...filters, offset: filters.offset + 20 }, preservedQuery)}#history`}>Siguientes →</Link> : null}
    </nav> : null}
  </Card>;
}
