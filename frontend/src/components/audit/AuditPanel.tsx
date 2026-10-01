import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { DateDivider } from "@/components/ui/DateDivider";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { FilterTabs } from "@/components/ui/FilterTabs";
import { MutedText } from "@/components/ui/Text";
import {
  AuditFilters,
  AuditPage,
  auditActionsForCategory,
  auditCategories,
  auditCategoryDescriptions,
  auditQuery,
} from "@/lib/audit";
import { AuditEvent } from "./AuditEvent";
import styles from "./AuditPanel.module.css";

export function AuditPanel({ page, filters, invalidRange }: { page: AuditPage; filters: AuditFilters; invalidRange: boolean }) {
  const groups = new Map<string, typeof page.items>();
  for (const entry of page.items) {
    const date = entry.created_at.slice(0, 10);
    groups.set(date, [...(groups.get(date) ?? []), entry]);
  }
  return <Card className={styles.panel}>
    <FilterTabs label="Áreas de auditoría" activeValue={filters.category}
      description={auditCategoryDescriptions[filters.category]}
      items={auditCategories.map((category) => ({ ...category,
        href: `/audit?${auditQuery({ ...filters, category: category.value, action: "", offset: 0 })}`,
      }))} />
    <form action="/audit" method="get" className={styles.filters}>
      <input type="hidden" name="category" value={filters.category} />
      <SelectField label="Acción" name="action" defaultValue={filters.action} options={[
        { value: "", label: "Todas las acciones" },
        ...auditActionsForCategory(filters.category).map(([value, label]) => ({ value, label })),
      ]} />
      <SelectField label="Persona" name="actor_user_id" defaultValue={filters.actor_user_id} options={[
        { value: "", label: "Todas las personas" },
        ...page.actors.map((actor) => ({ value: actor.id, label: actor.name })),
      ]} />
      <FormField label="Desde (UTC)" type="datetime-local" name="since" defaultValue={filters.since} />
      <FormField label="Hasta (UTC, inclusive)" type="datetime-local" name="until" defaultValue={filters.until} />
      <div className={styles.actions}><Button type="submit">Filtrar</Button><Link href="/audit">Limpiar filtros</Link></div>
    </form>
    {invalidRange ? <p role="alert">La fecha inicial no puede ser posterior a la final.</p> : <>
      <div className={styles.list}>{[...groups.entries()].map(([date, entries]) =>
        <section className={styles.dateGroup} key={date} aria-labelledby={`audit-date-${date}`}>
          <DateDivider date={date} id={`audit-date-${date}`} />
          <div className={styles.events}>{entries.map((entry) =>
            <AuditEvent key={entry.id} entry={entry} />)}</div>
        </section>)}
        {!page.items.length ? <MutedText>No hay eventos con estos filtros.</MutedText> : null}</div>
      {page.has_more || filters.offset > 0 ? <nav className={styles.pagination} aria-label="Páginas de auditoría">
        {filters.offset > 0 ? <Link href={`/audit?${auditQuery({ ...filters, offset: Math.max(0, filters.offset - 20) })}`}>← Anteriores</Link> : <span />}
        {page.has_more ? <Link href={`/audit?${auditQuery({ ...filters, offset: filters.offset + 20 })}`}>Siguientes →</Link> : null}
      </nav> : null}
    </>}
  </Card>;
}
