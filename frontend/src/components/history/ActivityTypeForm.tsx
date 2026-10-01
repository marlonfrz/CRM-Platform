"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { SelectField } from "@/components/ui/SelectField";
import { FormError, MutedText } from "@/components/ui/Text";
import { ActivityDepartment } from "@/lib/activities";
import { apiRequest } from "@/lib/client-api";

import styles from "./ActivityTypeForm.module.css";

export function ActivityTypeForm({ departments, onDone }: {
  departments: ActivityDepartment[];
  onDone: (saved?: boolean) => void;
}) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, startTransition] = useTransition();
  const busy = saving || refreshing;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSaving(true);
    setError("");
    try {
      const response = await apiRequest("/activity-types", {
        method: "POST",
        body: JSON.stringify({
          name: String(data.get("name") ?? "").trim(),
          department_id: data.get("departmentId") || null,
        }),
      });
      if (!response.ok) {
        setError(response.status === 409
          ? "Ya existe un tipo con ese nombre en el departamento."
          : "No se pudo crear el tipo de actividad.");
        return;
      }
      startTransition(() => router.refresh());
      onDone(true);
    } catch {
      setError("No se pudo conectar con el servidor.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <div>
        <h3>Nuevo tipo de actividad</h3>
        <MutedText>Se utilizará como opción y filtro, evitando nombres escritos de formas distintas.</MutedText>
      </div>
      <FormField label="Nombre" name="name" required maxLength={100} disabled={busy} />
      {departments.length ? (
        <SelectField label="Departamento" name="departmentId" required disabled={busy} options={[
          { value: "", label: "Selecciona un departamento" },
          ...departments.map((item) => ({ value: item.id, label: item.name })),
        ]} />
      ) : <input type="hidden" name="departmentId" value="" />}
      {error ? <FormError>{error}</FormError> : null}
      <div className={styles.actions}>
        <Button type="submit" disabled={busy}>{busy ? "Creando…" : "Crear tipo"}</Button>
        <Button type="button" variant="quiet" disabled={busy} onClick={() => onDone()}>Cancelar</Button>
      </div>
    </form>
  );
}
