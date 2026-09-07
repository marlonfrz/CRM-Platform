"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { FormError, MutedText } from "@/components/ui/Text";
import { Task, TaskOptions } from "@/lib/tasks";
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
  async function complete() {
    if (await mutate(`/clients/${task.client_id}/tasks/${task.id}/complete`, "POST")) {
      setConfirming(false);
      setMessage("Tarea completada.");
    }
  }
  return (
    <article className={styles.entry}>
      <header className={styles.header}>
        <div><h3>{task.title}</h3><MutedText>{task.assigned_to_name}{task.department_name ? ` · ${task.department_name}` : ""}</MutedText></div>
        <span className={pending ? styles.pending : styles.completed}>{pending ? "Pendiente" : "Completada"}</span>
      </header>
      {!options ? <Link href={`/clients/${task.client_id}#tasks`}>{task.client_name}</Link> : null}
      {editing && options && pending ? <TaskForm clientId={task.client_id} task={task} options={options} onDone={(saved) => {
        setEditing(false); if (saved) setMessage("Cambios guardados.");
      }} /> : (
        <>
          {task.description ? <p className={styles.description}>{task.description}</p> : null}
          <MutedText>{task.due_at ? `Fecha límite: ${formatUtcTimestamp(task.due_at)}` : "Sin fecha límite"}</MutedText>
          {task.completed_at ? <MutedText>Completada: {formatUtcTimestamp(task.completed_at)}</MutedText> : null}
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
