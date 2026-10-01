"use client";

import { FormEvent, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { TextareaField } from "@/components/ui/TextareaField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import {
  Activity,
  ActivityPage,
  ActivityStatus,
  activityFormBody,
  localDateValue,
} from "@/lib/activities";

import { RecurrenceFields } from "./RecurrenceFields";
import styles from "./activity-form.module.css";

type ActivityOptions = Pick<
  ActivityPage,
  "departments" | "candidates" | "activity_types" | "can_create"
>;

type Props = {
  clientId: string;
  options: ActivityOptions;
  activity?: Activity;
  onDone: (saved?: boolean) => void;
};

export function ActivityForm({ clientId, options, activity, onDone }: Props) {
  const router = useRouter();
  const [status, setStatus] = useState<ActivityStatus>(activity?.status ?? "PENDING");
  const [department, setDepartment] = useState(
    activity?.department_id ?? (options.departments.length === 1 ? options.departments[0].id : ""),
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const inFlight = useRef(false);
  const busy = saving || refreshing;
  const individual = options.departments.length === 0;
  const candidates = useMemo(() => options.candidates.filter(
    (candidate) => individual || candidate.department_ids.includes(department),
  ), [department, individual, options.candidates]);
  const activityTypes = options.activity_types.filter(
    (item) => item.department_id === null || item.department_id === department,
  );
  const selectedAssignee = activity?.assigned_to_user_id
    ?? (candidates.length === 1 ? candidates[0].id : "");
  const selectedType = activity?.activity_type_id
    ?? (activityTypes.length === 1 ? activityTypes[0].id : "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || busy) return;
    const data = new FormData(event.currentTarget);
    inFlight.current = true;
    setSaving(true);
    setError("");
    try {
      const response = await apiRequest(
        `/clients/${clientId}/activities${activity ? `/${activity.id}` : ""}`,
        {
          method: activity ? "PATCH" : "POST",
          body: JSON.stringify(activityFormBody(data, !!activity)),
        },
      );
      if (response.status === 401) { router.push("/login"); return; }
      if (!response.ok) {
        const errors: Record<number, string> = {
          403: "No tienes permiso o el responsable/tipo ya no está disponible.",
          404: "La actividad, el departamento, el tipo o el responsable ya no existe.",
          409: "Selecciona un departamento y un responsable disponibles.",
          422: "Revisa la fecha, la programación y los campos obligatorios.",
        };
        setError(errors[response.status] ?? "No se pudo guardar. Inténtalo de nuevo.");
        return;
      }
      startTransition(() => router.refresh());
      onDone(true);
    } catch {
      setError("No se pudo conectar. Tus datos siguen en el formulario.");
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-busy={busy}>
      {!activity ? (
        <SelectField label="Estado inicial" name="status" value={status} disabled={busy}
          onChange={(event) => setStatus(event.target.value as ActivityStatus)} options={[
            { value: "PENDING", label: "Pendiente" },
            { value: "COMPLETED", label: "Completada" },
          ]} />
      ) : null}

      {!activity && options.departments.length > 1 ? (
        <SelectField label="Departamento" name="departmentId" required value={department}
          disabled={busy} onChange={(event) => setDepartment(event.target.value)} options={[
            { label: "Selecciona un departamento", value: "" },
            ...options.departments.map((item) => ({ label: item.name, value: item.id })),
          ]} />
      ) : null}
      {!activity && options.departments.length === 1 ? (
        <>
          <input type="hidden" name="departmentId" value={department} />
          <MutedText>Departamento: {options.departments[0].name}</MutedText>
        </>
      ) : null}

      <div className={styles.fields}>
        <SelectField key={`${department}:${selectedType}`} label="Tipo" name="activityTypeId"
          required defaultValue={selectedType} disabled={busy || !activityTypes.length} options={[
            { value: "", label: activityTypes.length ? "Selecciona un tipo" : "No hay tipos disponibles" },
            ...activityTypes.map((item) => ({ value: item.id, label: item.name })),
          ]} />
        <FormField label="Fecha programada" name="scheduledFor" type="date" required
          defaultValue={activity?.scheduled_for ?? localDateValue()} disabled={busy} />
      </div>

      <FormField label={status === "PENDING" ? "Título" : "Título (opcional)"} name="title"
        required={status === "PENDING"} maxLength={200} defaultValue={activity?.title ?? ""}
        disabled={busy} />

      {!activity ? (
        candidates.length === 1 ? (
          <>
            <input type="hidden" name="assignee" value={selectedAssignee} />
            <MutedText>Responsable: {candidates[0].name}</MutedText>
          </>
        ) : (
          <SelectField key={`${department}:${candidates.map((item) => item.id).join(",")}`}
            label="Responsable" name="assignee" required disabled={busy || !candidates.length}
            defaultValue={selectedAssignee} options={[
              { value: "", label: candidates.length
                ? "Selecciona un responsable" : "No hay responsables disponibles" },
              ...candidates.map((item) => ({ value: item.id, label: item.name })),
            ]} />
        )
      ) : <input type="hidden" name="assignee" value={selectedAssignee} />}

      <TextareaField label="Descripción" name="description" required maxLength={5000}
        defaultValue={activity?.description ?? ""} disabled={busy} />
      <TextareaField label="Próxima acción (opcional)" name="nextAction" maxLength={2000}
        defaultValue={activity?.next_action ?? ""} disabled={busy} />

      {status === "COMPLETED" && activity ? (
        <FormField label="Fecha y hora de realización" name="occurredAt" type="datetime-local"
          defaultValue={activity.occurred_at
            ? new Date(activity.occurred_at).toISOString().slice(0, 16) : ""} disabled={busy} />
      ) : null}
      {!activity && status === "PENDING" ? <RecurrenceFields disabled={busy} /> : null}

      {error ? <FormError>{error}</FormError> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={busy || !candidates.length || !activityTypes.length}>
          {busy ? "Guardando…" : activity ? "Guardar cambios" : "Guardar actividad"}
        </Button>
        <Button type="button" variant="quiet" disabled={busy} onClick={() => onDone()}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
