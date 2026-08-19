"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { FormError } from "@/components/ui/Text";

import styles from "./setup-form.module.css";

export function SetupForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"INDIVIDUAL" | "BUSINESS">("BUSINESS");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("ownerPassword") ?? "");
    const passwordConfirmation = String(data.get("ownerPasswordConfirmation") ?? "");
    if (password !== passwordConfirmation) {
      setError("Las contraseñas no coinciden.");
      setSubmitting(false);
      return;
    }
    const response = await fetch("/api/backend/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode,
        organization_name: data.get("organizationName"),
        owner_name: data.get("ownerName"),
        owner_email: data.get("ownerEmail"),
        owner_password: password,
        owner_password_confirmation: passwordConfirmation,
      }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setError(response.status === 409 ? "Esta instalación ya está configurada." : "No se pudo completar la configuración.");
      return;
    }
    router.replace("/login?setup=complete");
    router.refresh();
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <fieldset>
        <legend>¿Cómo vas a utilizar el CRM?</legend>
        <div className={styles.modeGrid}>
          <label className={`${styles.modeOption} ${mode === "INDIVIDUAL" ? styles.selected : ""}`}>
            <input type="radio" name="mode" value="INDIVIDUAL" checked={mode === "INDIVIDUAL"} onChange={() => setMode("INDIVIDUAL")} />
            <strong>Uso personal</strong><span>Sin departamentos ni gestión de equipo.</span>
          </label>
          <label className={`${styles.modeOption} ${mode === "BUSINESS" ? styles.selected : ""}`}>
            <input type="radio" name="mode" value="BUSINESS" checked={mode === "BUSINESS"} onChange={() => setMode("BUSINESS")} />
            <strong>Empresa</strong><span>Con usuarios, departamentos y permisos.</span>
          </label>
        </div>
      </fieldset>
      <div className={styles.fieldGrid}>
        <FormField label="Nombre de la organización" name="organizationName" required maxLength={200} />
        <FormField label="Tu nombre completo" name="ownerName" autoComplete="name" required maxLength={200} />
        <FormField label="Correo de acceso" name="ownerEmail" type="email" autoComplete="email" required />
        <FormField label="Contraseña inicial" name="ownerPassword" type={showPasswords ? "text" : "password"} autoComplete="new-password" minLength={12} required hint="Mínimo 12 caracteres." />
        <FormField label="Repite la contraseña" name="ownerPasswordConfirmation" type={showPasswords ? "text" : "password"} autoComplete="new-password" minLength={12} required />
      </div>
      <div className={styles.passwordActions}>
        <Button type="button" variant="quiet" onClick={() => setShowPasswords((visible) => !visible)}>
          {showPasswords ? "Ocultar contraseñas" : "Mostrar contraseñas"}
        </Button>
      </div>
      {error ? <FormError>{error}</FormError> : null}
      <Button className={styles.submit} type="submit" disabled={submitting}>{submitting ? "Configurando…" : "Crear instalación"}</Button>
    </form>
  );
}
