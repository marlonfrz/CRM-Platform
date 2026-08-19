"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const response = await fetch("/api/backend/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
    });
    setSubmitting(false);
    if (!response.ok) {
      setError(response.status === 401 ? "El correo o la contraseña no son correctos." : "No se pudo iniciar sesión.");
      return;
    }
    router.replace("/dashboard");
    router.refresh();
  }

  return (
    <form className="login-form" onSubmit={submit}>
      <label>
        Correo electrónico
        <input name="email" type="email" autoComplete="email" required />
      </label>
      <label>
        Contraseña
        <input name="password" type="password" autoComplete="current-password" required />
      </label>
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      <button type="submit" disabled={submitting}>
        {submitting ? "Entrando…" : "Entrar"}
      </button>
    </form>
  );
}
