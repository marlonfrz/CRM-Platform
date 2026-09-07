"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { TextareaField } from "@/components/ui/TextareaField";
import { FormError, MutedText } from "@/components/ui/Text";
import { Task, TaskOptions, taskFormBody } from "@/lib/tasks";
import { useTaskMutation } from "./useTaskMutation";
import styles from "./TaskForm.module.css";

type Props = { clientId: string; options: TaskOptions; task?: Task; onDone: (saved?: boolean) => void };

export function TaskForm({ clientId, options, task, onDone }: Props) {
  const [department, setDepartment] = useState(task?.department_id ?? (options.departments.length === 1 ? options.departments[0].id : ""));
  const { mutate, busy, error } = useTaskMutation();
  const candidates = options.candidates.filter((u) => options.individual || u.department_ids.includes(department));
  const selected = task?.assigned_to_user_id ?? (candidates.length === 1 ? candidates[0].id : "");
  const choices = candidates.map((u) => ({ value: u.id, label: u.name }));
  if (task && !candidates.some((u) => u.id === task.assigned_to_user_id)) {
    choices.unshift({ value: task.assigned_to_user_id, label: `${task.assigned_to_name} (responsable actual)` });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (await mutate(`/clients/${clientId}/tasks${task ? `/${task.id}` : ""}`, task ? "PATCH" : "POST", () => taskFormBody(data, !!task))) onDone(true);
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-busy={busy}>
      <FormField label="Título" name="title" required maxLength={200} defaultValue={task?.title ?? ""} disabled={busy} />
      <TextareaField label="Descripción (opcional)" name="description" maxLength={5000} defaultValue={task?.description ?? ""} disabled={busy} />
      {!task && !options.individual && options.departments.length > 1 ? <SelectField label="Departamento" name="department" required value={department} disabled={busy}
        onChange={(event) => setDepartment(event.target.value)}
        options={[{ value: "", label: "Selecciona un departamento" }, ...options.departments.map((d) => ({ value: d.id, label: d.name }))]} />
        : !task ? <input type="hidden" name="department" value={department} /> : null}
      {!options.individual && (task?.department_name || options.departments.length === 1) ? <MutedText>Departamento: {task?.department_name ?? options.departments[0]?.name}</MutedText> : null}
      <div className={styles.fields}>
        {options.individual || choices.length === 1 ? (
          <><input type="hidden" name="assignee" value={selected} /><MutedText>Responsable: {choices[0]?.label ?? "Tú"}</MutedText></>
        ) : <SelectField key={department + choices.map((u) => u.value).join(",")} label="Responsable" name="assignee" required disabled={busy || !choices.length}
          defaultValue={selected} options={[{ value: "", label: "Selecciona un responsable" }, ...choices]} />}
        <FormField label="Fecha límite (UTC, opcional)" name="dueAt" type="datetime-local" step="any"
          defaultValue={task?.due_at ? new Date(task.due_at).toISOString().slice(0, -1) : ""} disabled={busy} />
      </div>
      {!task && !candidates.length ? <MutedText>No hay responsables disponibles para este departamento. Un empleado necesita tener asignado el cliente.</MutedText> : null}
      {error ? <FormError>{error}</FormError> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={busy || (!task && !candidates.length)}>{busy ? "Guardando…" : task ? "Guardar cambios" : "Crear tarea"}</Button>
        <Button type="button" variant="quiet" disabled={busy} onClick={() => onDone()}>Cancelar</Button>
      </div>
    </form>
  );
}
