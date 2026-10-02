"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { FormError, MutedText } from "@/components/ui/Text";
import { Task, TaskOptions } from "@/lib/tasks";
import { ActivityView, activityDate } from "@/lib/activities";
import { formatUtcTimestamp } from "@/lib/date-time";
import { TaskForm } from "./TaskForm";
import { useTaskMutation } from "./useTaskMutation";
import styles from "./TaskEntry.module.css";

export function TaskEntry({ task, options }: { task: Task; options: TaskOptions | null }) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState("");
  const { mutate, error, busy } = useTaskMutation();
  const pending = task.status === "PENDING";
  const today = new Date().toISOString().slice(0, 10);
  const dueDate = task.due_at?.slice(0, 10);
  const view: ActivityView = !dueDate || dueDate === today
    ? "TODAY" : dueDate > today ? "SCHEDULED" : "HISTORY";
  async function complete() {
    if (await mutate(`/clients/${task.client_id}/tasks/${task.id}/complete`, "POST")) {
      setConfirming(false);
      setMessage("Tarea completada.");
    }
  }
  return (
    <article className={styles.entry}>
      <header className={styles.header}>
        <div><span className={pending ? styles.pending : styles.completed}>{pending ? "Pendiente" : "Completada"}</span>
          <h3>{task.title}</h3></div>
        <time>{task.due_at ? activityDate(task.due_at) : "Sin fecha programada"}</time>
      </header>
      {editing && options && pending ? <TaskForm clientId={task.client_id} task={task} options={options} onDone={(saved) => {
        setEditing(false); if (saved) setMessage("Cambios guardados.");
      }} /> : (
        <>
          {task.description ? <p className={styles.description}>{task.description}</p> : null}
          <p className={styles.meta}>{!options ? <Link href={`/clients/${task.client_id}?tracking_view=${view}#tracking`}>{task.client_name}</Link> : null}
            {!options ? " · " : ""}{task.assigned_to_name}{task.department_name ? ` · ${task.department_name}` : ""}</p>
          {task.completed_at ? <MutedText className={styles.timestamp}>Completada: {formatUtcTimestamp(task.completed_at)}</MutedText> : null}
          {pending ? <div className={styles.actions}>
            {confirming ? <><p>¿Marcar esta tarea como completada?</p>
              <Button type="button" disabled={busy} onClick={() => void complete()}>Confirmar finalización</Button>
              <Button type="button" variant="quiet" disabled={busy} onClick={() => setConfirming(false)}>Cancelar</Button></>
              : <><Button type="button" disabled={busy} onClick={() => { setMessage(""); setConfirming(true); }}>Completar tarea</Button>
                {options ? <Button type="button" variant="quiet" disabled={busy} onClick={() => { setMessage(""); setEditing(true); }}>Editar tarea</Button> : null}</>}
          </div> : null}
        </>
      )}
      {error ? <FormError>{error}</FormError> : null}
      {message ? <p role="status">{message}</p> : null}
    </article>
  );
}
