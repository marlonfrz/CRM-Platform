"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { FormError } from "@/components/ui/Text";

import styles from "./login-form.module.css";

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
    <form className={styles.form} onSubmit={submit}>
      <FormField label="Correo electrónico" name="email" type="email" autoComplete="email" required />
      <FormField label="Contraseña" name="password" type="password" autoComplete="current-password" required />
      {error ? <FormError>{error}</FormError> : null}
      <Button type="submit" disabled={submitting}>
        {submitting ? "Entrando…" : "Entrar"}
      </Button>
    </form>
  );
}
