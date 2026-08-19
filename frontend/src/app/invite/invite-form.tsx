"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { PasswordConfirmationFields } from "@/components/forms/PasswordConfirmationFields";
import { Button } from "@/components/ui/Button";
import { FormError } from "@/components/ui/Text";
import { apiRequest } from "@/lib/client-api";

import styles from "./invite-form.module.css";

export function InviteForm({ token }: { token: string }) {
  const router = useRouter();
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    const confirmation = String(data.get("passwordConfirmation") ?? "");
    if (password !== confirmation) { setError("Las contraseñas no coinciden."); return; }
    const response = await apiRequest("/auth/invitations/accept", {
      method: "POST",
      body: JSON.stringify({ token, password, password_confirmation: confirmation }),
    });
    if (!response.ok) { setError("La invitación no es válida o ha caducado."); return; }
    router.replace("/login");
    router.refresh();
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <div className={styles.fields}>
        <PasswordConfirmationFields passwordName="password" confirmationName="passwordConfirmation" />
      </div>
      {error ? <FormError>{error}</FormError> : null}
      <Button type="submit">Activar mi cuenta</Button>
    </form>
  );
}
