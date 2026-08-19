"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";

import styles from "./PasswordConfirmationFields.module.css";

type Props = {
  confirmationName: string;
  passwordName: string;
};

export function PasswordConfirmationFields({ confirmationName, passwordName }: Props) {
  const [visible, setVisible] = useState(false);
  const type = visible ? "text" : "password";
  return (
    <div className={styles.fields}>
      <FormField label="Contraseña" name={passwordName} type={type} autoComplete="new-password" minLength={12} required hint="Mínimo 12 caracteres." />
      <FormField label="Repite la contraseña" name={confirmationName} type={type} autoComplete="new-password" minLength={12} required />
      <div className={styles.actions}>
        <Button type="button" variant="quiet" onClick={() => setVisible((value) => !value)}>
          {visible ? "Ocultar contraseñas" : "Mostrar contraseñas"}
        </Button>
      </div>
    </div>
  );
}
