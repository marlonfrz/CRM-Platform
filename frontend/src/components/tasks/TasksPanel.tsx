"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField } from "@/components/ui/SelectField";
import { MutedText } from "@/components/ui/Text";
import { TaskFilters, TaskPage, taskPageQuery, taskStatusOptions } from "@/lib/tasks";
import { TaskForm } from "./TaskForm";
import { TaskEntry } from "./TaskEntry";
import styles from "./TasksPanel.module.css";

type Props = { page: TaskPage; filters: TaskFilters; clientId?: string; preservedQuery?: string };

export function TasksPanel({ page, filters, clientId, preservedQuery = "" }: Props) {
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const path = clientId ? `/clients/${clientId}` : "/tasks";
  const canCreate = !!clientId && !!page.options?.candidates.length;
  const orderedTasks = [...page.items].sort((left, right) =>
    left.status === right.status ? 0 : left.status === "PENDING" ? -1 : 1,
  );
  return (
    <Card className={styles.card} id="tasks" aria-label={clientId ? "Tareas del cliente" : "Mis tareas"}>
      <header className={styles.header}><div><h2>{clientId ? "Tareas del cliente" : "Trabajo pendiente y completado"}</h2>
        <MutedText>Primero las pendientes; después, las completadas, por fecha programada.</MutedText></div>
        {canCreate && !creating ? <Button type="button" onClick={() => { setMessage(""); setCreating(true); }}>Nueva tarea</Button> : null}
      </header>
      {creating && clientId && page.options ? <div className={styles.editor}>
        <TaskForm clientId={clientId} options={page.options} onDone={(saved) => { setCreating(false); if (saved) setMessage("Tarea creada. El listado respeta el filtro de estado seleccionado."); }} />
      </div> : null}
      {clientId && !canCreate ? <MutedText>No hay responsables disponibles. Comprueba los departamentos y las asignaciones del cliente.</MutedText> : null}
      {message ? <p role="status">{message}</p> : null}
      <form className={styles.filters} action={`${path}#tasks`} method="get" key={filters.status}>
        {Array.from(new URLSearchParams(preservedQuery)).map(([key, value]) => <input key={key} type="hidden" name={key} value={value} />)}
        <SelectField label="Estado" name="task_status" defaultValue={filters.status} options={taskStatusOptions} />
        <Button type="submit" variant="quiet">Filtrar tareas</Button>
      </form>
      <div className={styles.list}>
        {orderedTasks.map((task) => <TaskEntry key={task.id} task={task} options={page.options ?? null} />)}
        {!page.items.length ? <MutedText className={styles.empty}>No hay tareas visibles con este filtro.</MutedText> : null}
      </div>
      {filters.offset > 0 || page.has_more ? <nav className={styles.pagination} aria-label="Páginas de tareas">
        {filters.offset > 0 ? <Link href={`${path}?${taskPageQuery({ ...filters, offset: Math.max(0, filters.offset - 20) }, preservedQuery)}#tasks`}>← Anteriores</Link> : <span />}
        {page.has_more ? <Link href={`${path}?${taskPageQuery({ ...filters, offset: filters.offset + 20 }, preservedQuery)}#tasks`}>Siguientes →</Link> : null}
      </nav> : null}
    </Card>
  );
}
