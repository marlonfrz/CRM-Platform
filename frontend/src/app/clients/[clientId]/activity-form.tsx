"use client";

import { FormEvent, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { TextareaField } from "@/components/ui/TextareaField";
import { FormError, MutedText } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";
import { Activity, ActivityDepartment, activityFormBody, activityTypeOptions } from "@/lib/activities";

import styles from "./activity-form.module.css";

type Props = {
  clientId: string; departments: ActivityDepartment[]; activity?: Activity; onDone: (saved?: boolean) => void;
};

export function ActivityForm({ clientId, departments, activity, onDone }: Props) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [refreshing, startTransition] = useTransition();
  const inFlight = useRef(false);
  const busy = saving || refreshing;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || busy) return;
    const data = new FormData(event.currentTarget);
    inFlight.current = true;
    setSaving(true);
    setError("");
    try {
      const response = await apiRequest(`/clients/${clientId}/activities${activity ? `/${activity.id}` : ""}`, {
        method: activity ? "PATCH" : "POST", body: JSON.stringify(activityFormBody(data, !!activity)),
      });
      if (response.status === 401) { router.push("/login"); return; }
      if (!response.ok) {
        const errors: Record<number, string> = {
          403: "No tienes permiso para esta acción o han transcurrido las 24 horas de corrección.",
          404: "La actividad, el cliente o el departamento ya no están disponibles.",
          409: "Selecciona un departamento disponible. Si tus permisos han cambiado, recarga la ficha.",
          422: "Revisa el tipo, la fecha y la longitud de los textos.",
        };
        setError(errors[response.status] ?? "No se pudo guardar. Inténtalo de nuevo.");
        return;
      }
      startTransition(() => router.refresh());
      onDone(true);
    } catch {
      setError("No se pudo conectar o la fecha no es válida. Tus datos siguen en el formulario.");
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-busy={busy}>
      <div className={styles.fields}>
        <SelectField label="Tipo de actividad" name="type" defaultValue={activity?.type ?? "NOTE"} options={activityTypeOptions} disabled={busy} />
        <FormField label="Fecha y hora de la interacción (UTC)" name="occurredAt" type="datetime-local" step="any"
          defaultValue={activity ? new Date(activity.occurred_at).toISOString().slice(0, -1) : ""}
          required={!!activity} disabled={busy} />
      </div>
      {!activity ? <MutedText>Si dejas la fecha vacía, se registra la hora actual.</MutedText> : null}
      {!activity && departments.length > 1 ? (
        <SelectField label="Departamento" name="departmentId" required defaultValue="" disabled={busy}
          options={[{ label: "Selecciona un departamento", value: "" }, ...departments.map((d) => ({ label: d.name, value: d.id }))]} />
      ) : null}
      {!activity && departments.length === 1 ? <MutedText>Departamento: {departments[0].name}</MutedText> : null}
      <TextareaField label="Descripción" name="description" required maxLength={5000} defaultValue={activity?.description ?? ""} disabled={busy} />
      <TextareaField label="Próxima acción (opcional)" name="nextAction" maxLength={2000} defaultValue={activity?.next_action ?? ""} disabled={busy} />
      {error ? <FormError>{error}</FormError> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={busy}>{busy ? "Guardando…" : activity ? "Guardar corrección" : "Registrar actividad"}</Button>
        <Button type="button" variant="quiet" disabled={busy} onClick={() => onDone()}>Cancelar</Button>
      </div>
    </form>
  );
}
