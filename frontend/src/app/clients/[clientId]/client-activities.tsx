"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { ActivityFilters, ActivityPage, activityQuery, activityTypeOptions } from "@/lib/activities";
import { ActivityEntry } from "./activity-entry";
import { ActivityForm } from "./activity-form";
import styles from "./client-activities.module.css";

type Props = { clientId: string; page: ActivityPage; filters: ActivityFilters };

export function ClientActivities({ clientId, page, filters }: Props) {
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const path = `/clients/${clientId}`;
  return (
    <Card className={styles.card} id="activities" aria-label="Actividades del cliente">
      <header className={styles.header}>
        <div><h2>Actividades</h2><MutedText>Interacciones y anotaciones de este cliente.</MutedText></div>
        {page.can_create && !creating ? <Button type="button" onClick={() => { setMessage(""); setCreating(true); }}>Nueva actividad</Button> : null}
      </header>
      {creating && page.can_create ? <div className={styles.editor}><ActivityForm clientId={clientId} departments={page.departments} onDone={(saved) => {
        setCreating(false);
        if (saved) setMessage("Actividad registrada. El listado respeta los filtros y el orden por fecha de la interacción.");
      }} /></div> : null}
      {message ? <p role="status">{message}</p> : null}
      {!page.can_create ? <MutedText>Necesitas pertenecer a un departamento para registrar actividad. Si eres propietario, crea primero un departamento.</MutedText> : null}
      <form className={styles.filters} action={`${path}#activities`} method="get" key={`${filters.type}:${filters.department}`}>
        <SelectField label="Tipo" name="activity_type" defaultValue={filters.type} options={[{ label: "Todos los tipos", value: "" }, ...activityTypeOptions]} />
        {page.departments.length > 1 ? <SelectField label="Departamento" name="department_id" defaultValue={filters.department}
          options={[{ label: "Todos los permitidos", value: "" }, ...page.departments.map((d) => ({ label: d.name, value: d.id }))]} /> : null}
        <Button type="submit" variant="quiet">Filtrar</Button>
      </form>
      <div className={styles.list}>
        {page.items.map((activity) => <ActivityEntry key={activity.id} activity={activity} clientId={clientId} />)}
        {!page.items.length ? <MutedText className={styles.empty}>No hay actividades visibles con estos filtros.</MutedText> : null}
      </div>
      {filters.offset > 0 || page.has_more ? <nav className={styles.pagination} aria-label="Páginas de actividades">
        {filters.offset > 0 ? <Link href={`${path}?${activityQuery({ ...filters, offset: Math.max(0, filters.offset - 20) })}#activities`}>← Anteriores</Link> : <span />}
        {page.has_more ? <Link href={`${path}?${activityQuery({ ...filters, offset: filters.offset + 20 })}#activities`}>Siguientes →</Link> : null}
      </nav> : null}
    </Card>
  );
}
