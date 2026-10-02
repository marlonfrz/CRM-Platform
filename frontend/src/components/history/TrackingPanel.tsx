"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ActivityEntry } from "@/app/clients/[clientId]/activity-entry";
import { ActivityForm } from "@/app/clients/[clientId]/activity-form";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DateDivider } from "@/components/ui/DateDivider";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import {
  Activity,
  ActivityFilters,
  ActivityPage,
  ActivityView,
  activityPageQuery,
  activityQuery,
} from "@/lib/activities";

import { ActivityTypeForm } from "./ActivityTypeForm";
import { ActivityOptionsProvider } from "./ActivityOptionsStore";
import styles from "./TrackingPanel.module.css";

type Props = {
  clientId: string;
  page: ActivityPage;
  filters: ActivityFilters;
};

const views: { value: ActivityView; label: string }[] = [
  { value: "TODAY", label: "Hoy" },
  { value: "SCHEDULED", label: "Programadas" },
  { value: "HISTORY", label: "Historial" },
];

const emptyMessages: Record<ActivityView, string> = {
  TODAY: "No hay actividad para hoy con estos filtros.",
  SCHEDULED: "No hay próximas actividades programadas.",
  HISTORY: "No hay actividad anterior con estos filtros.",
};

function groupActivities(items: Activity[]) {
  const groups = new Map<string, Activity[]>();
  for (const activity of items) {
    groups.set(activity.scheduled_for, [
      ...(groups.get(activity.scheduled_for) ?? []),
      activity,
    ]);
  }
  return [...groups.entries()];
}

export function TrackingPanel({ clientId, page, filters }: Props) {
  const router = useRouter();
  const [editor, setEditor] = useState<"ACTIVITY" | "TYPE" | null>(null);
  const [message, setMessage] = useState("");
  const [items, setItems] = useState(page.items);
  const [hasMore, setHasMore] = useState(page.has_more);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadError, setLoadError] = useState("");
  const departments = page.departments;
  const activityTypes = page.activity_types;
  const options = useMemo(() => ({
    departments,
    candidates: page.candidates,
    activity_types: activityTypes,
    can_create: page.can_create,
  }), [departments, page.candidates, activityTypes, page.can_create]);
  const groups = useMemo(() => groupActivities(items), [items]);

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    setLoadError("");
    try {
      const response = await apiRequest(
        `/clients/${clientId}/activities?${activityQuery(filters, items.length)}`,
      );
      if (response.status === 401) {
        router.push("/login");
        return;
      }
      if (!response.ok) {
        setLoadError("No se pudieron cargar más actividades.");
        return;
      }
      const nextPage = await response.json() as ActivityPage;
      setItems((current) => {
        const known = new Set(current.map((activity) => activity.id));
        return [...current, ...nextPage.items.filter((activity) => !known.has(activity.id))];
      });
      setHasMore(nextPage.has_more);
    } catch {
      setLoadError("No se pudo conectar con el servidor.");
    } finally {
      setLoadingMore(false);
    }
  }

  const content = (
    <Card className={styles.card} id="tracking" aria-label="Seguimiento del cliente">
      <header className={styles.header}>
        <div>
          <h2>Seguimiento del cliente</h2>
          <MutedText>Consulta la actividad por fecha sin alargar innecesariamente la ficha.</MutedText>
        </div>
        <div className={styles.headerActions}>
          {page.can_manage_types ? (
            <Button type="button" variant="quiet" disabled={editor !== null}
              onClick={() => { setMessage(""); setEditor("TYPE"); }}>Nuevo tipo</Button>
          ) : null}
          {page.can_create ? (
            <Button type="button" disabled={editor !== null}
              onClick={() => { setMessage(""); setEditor("ACTIVITY"); }}>Nueva actividad</Button>
          ) : null}
        </div>
      </header>

      {editor === "ACTIVITY" ? (
        <div className={styles.editor}>
          <ActivityForm clientId={clientId} onDone={(saved) => {
            setEditor(null);
            if (saved) setMessage("Actividad guardada.");
          }} />
        </div>
      ) : null}
      {editor === "TYPE" ? (
        <div className={styles.editor}>
          <ActivityTypeForm departments={departments} onDone={(saved) => {
            setEditor(null);
            if (saved) setMessage("Tipo de actividad creado.");
          }} />
        </div>
      ) : null}
      {!page.can_create ? (
        <MutedText>No hay departamentos o responsables disponibles para registrar actividad.</MutedText>
      ) : null}
      {message ? <p role="status">{message}</p> : null}

      <nav className={styles.tabs} aria-label="Vista del seguimiento">
        {views.map((view) => (
          <Link key={view.value}
            className={`${styles.tab} ${filters.view === view.value ? styles.activeTab : ""}`}
            aria-current={filters.view === view.value ? "page" : undefined}
            href={`/clients/${clientId}?${activityPageQuery({ ...filters, view: view.value })}#tracking`}>
            {view.label}
          </Link>
        ))}
      </nav>

      <form action={`/clients/${clientId}#tracking`} method="get" className={styles.filters}
        key={`${filters.type}:${filters.department}:${filters.view}`}>
        <input type="hidden" name="tracking_view" value={filters.view} />
        <SelectField label="Tipo de actividad" name="tracking_type" defaultValue={filters.type}
          options={[
            { value: "", label: "Todos los tipos" },
            ...activityTypes.map((item) => ({ value: item.id, label: item.name })),
          ]} />
        {departments.length > 1 ? (
          <SelectField label="Departamento" name="tracking_department"
            defaultValue={filters.department} options={[
              { value: "", label: "Todos los departamentos" },
              ...departments.map((item) => ({ value: item.id, label: item.name })),
            ]} />
        ) : null}
        <Button type="submit" variant="quiet">Aplicar filtros</Button>
        {(filters.type || filters.department) ? (
          <Link className={styles.clear}
            href={`/clients/${clientId}?${activityPageQuery({
              type: "",
              department: "",
              view: filters.view,
            })}#tracking`}>Limpiar</Link>
        ) : null}
      </form>

      <div className={styles.timeline} aria-live="polite">
        {groups.map(([date, activities]) => (
          <section className={styles.dateGroup} key={date} aria-labelledby={`date-${date}`}>
            <DateDivider date={date} id={`date-${date}`} />
            <div className={styles.list}>
              {activities.map((activity) => (
                <ActivityEntry key={activity.id} clientId={clientId} activity={activity} />
              ))}
            </div>
          </section>
        ))}
        {!items.length ? (
          <MutedText className={styles.empty}>{emptyMessages[filters.view]}</MutedText>
        ) : null}
      </div>

      {loadError ? <p className={styles.loadError} role="alert">{loadError}</p> : null}
      {hasMore ? (
        <div className={styles.loadMore}>
          <Button type="button" variant="quiet" disabled={loadingMore} onClick={loadMore}>
            {loadingMore ? "Cargando…" : "Ver más"}
          </Button>
        </div>
      ) : null}
    </Card>
  );
  return <ActivityOptionsProvider options={options}>{content}</ActivityOptionsProvider>;
}
