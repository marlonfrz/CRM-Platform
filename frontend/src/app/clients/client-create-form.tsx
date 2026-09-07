"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { TextareaField } from "@/components/ui/TextareaField";
import { FormError } from "@/components/ui/Text";
import type { Client } from "@/lib/clients";
import { apiRequest } from "@/lib/client-api";

import styles from "./client-create-form.module.css";

export function ClientCreateForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const formData = new FormData(event.currentTarget);
    const response = await apiRequest("/clients", {
      method: "POST",
      body: JSON.stringify({
        name: formData.get("name"),
        address: formData.get("address"),
        notes: formData.get("notes"),
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setError(response.status === 403 ? "No tienes permiso para crear clientes." : "No se pudo crear el cliente.");
      return;
    }
    const client = (await response.json()) as Client;
    router.push(`/clients/${client.id}`);
    router.refresh();
  }

  return (
    <Card className={styles.card}>
      <div className={styles.heading}>
        <h2>Nuevo cliente</h2>
        <p>Crea la ficha general. Después podrás añadir sus personas de contacto.</p>
      </div>
      <form className={styles.form} onSubmit={submit}>
        <FormField label="Nombre" name="name" required maxLength={200} />
        <FormField label="Dirección" name="address" maxLength={500} />
        <TextareaField className={styles.notes} label="Notas" name="notes" maxLength={5000} />
        {error ? <FormError className={styles.feedback}>{error}</FormError> : null}
        <div className={styles.actions}>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creando…" : "Crear cliente"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
