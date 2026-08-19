"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function SetupForm() {
  const router = useRouter();
  const [mode, setMode] = useState<"INDIVIDUAL" | "BUSINESS">("BUSINESS");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const response = await fetch("/api/backend/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode,
        organization_name: data.get("organizationName"),
        owner_name: data.get("ownerName"),
        owner_email: data.get("ownerEmail"),
        owner_password: data.get("ownerPassword"),
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
    <form className="setup-form" onSubmit={submit}>
      <fieldset>
        <legend>¿Cómo vas a utilizar el CRM?</legend>
        <div className="mode-grid">
          <label className={mode === "INDIVIDUAL" ? "mode-option selected" : "mode-option"}>
            <input type="radio" name="mode" value="INDIVIDUAL" checked={mode === "INDIVIDUAL"} onChange={() => setMode("INDIVIDUAL")} />
            <strong>Uso personal</strong><span>Sin departamentos ni gestión de equipo.</span>
          </label>
          <label className={mode === "BUSINESS" ? "mode-option selected" : "mode-option"}>
            <input type="radio" name="mode" value="BUSINESS" checked={mode === "BUSINESS"} onChange={() => setMode("BUSINESS")} />
            <strong>Empresa</strong><span>Con usuarios, departamentos y permisos.</span>
          </label>
        </div>
      </fieldset>
      <div className="form-grid">
        <label>Nombre de la organización<input name="organizationName" required maxLength={200} /></label>
        <label>Tu nombre completo<input name="ownerName" autoComplete="name" required maxLength={200} /></label>
        <label>Correo de acceso<input name="ownerEmail" type="email" autoComplete="email" required /></label>
        <label>Contraseña inicial<input name="ownerPassword" type="password" autoComplete="new-password" minLength={12} required /><small>Mínimo 12 caracteres.</small></label>
      </div>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <button type="submit" disabled={submitting}>{submitting ? "Configurando…" : "Crear instalación"}</button>
    </form>
  );
}
