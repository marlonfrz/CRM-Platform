import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { AuditFilters, AuditPage, auditActions, auditQuery } from "@/lib/audit";
import { AuditEvent } from "./AuditEvent";
import styles from "./AuditPanel.module.css";

export function AuditPanel({ page, filters, invalidRange }: { page: AuditPage; filters: AuditFilters; invalidRange: boolean }) {
  return <Card className={styles.panel}>
    <form action="/audit" method="get" className={styles.filters}>
      <SelectField label="Acción" name="action" defaultValue={filters.action} options={[
        { value: "", label: "Todas las acciones" }, ...Object.entries(auditActions).map(([value, label]) => ({ value, label })),
      ]} />
      <FormField label="ID del autor" name="actor_user_id" defaultValue={filters.actor_user_id} placeholder="UUID del usuario" />
      <FormField label="ID del recurso" name="entity_id" defaultValue={filters.entity_id} placeholder="UUID del recurso" />
      <FormField label="Desde (UTC)" type="datetime-local" name="since" defaultValue={filters.since} />
      <FormField label="Hasta (UTC, inclusive)" type="datetime-local" name="until" defaultValue={filters.until} />
      <div className={styles.actions}><Button type="submit">Filtrar</Button><Link href="/audit">Limpiar filtros</Link></div>
    </form>
    {invalidRange ? <p role="alert">La fecha inicial no puede ser posterior a la final.</p> : <>
      <div className={styles.list}>{page.items.map((entry) => <AuditEvent key={entry.id} entry={entry} />)}
        {!page.items.length ? <MutedText>No hay eventos con estos filtros.</MutedText> : null}</div>
      {page.has_more || filters.offset > 0 ? <nav className={styles.pagination} aria-label="Páginas de auditoría">
        {filters.offset > 0 ? <Link href={`/audit?${auditQuery({ ...filters, offset: Math.max(0, filters.offset - 20) })}`}>← Anteriores</Link> : <span />}
        {page.has_more ? <Link href={`/audit?${auditQuery({ ...filters, offset: filters.offset + 20 })}`}>Siguientes →</Link> : null}
      </nav> : null}
    </>}
  </Card>;
}
