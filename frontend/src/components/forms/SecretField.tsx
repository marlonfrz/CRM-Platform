"use client";

import { useId, useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Button } from "@/components/ui/Button";
import styles from "./SecretField.module.css";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
  hint?: string;
  revealLabel?: string;
};

export function SecretField({ label, hint, revealLabel = "token", ...props }: Props) {
  const [visible, setVisible] = useState(false);
  const generatedId = useId();
  const inputId = props.id ?? generatedId;
  return <div className={styles.field}>
    <label htmlFor={inputId}>{label}</label>
    <div className={styles.control}>
      <input {...props} id={inputId} className={styles.input} type={visible ? "text" : "password"} />
      <Button type="button" variant="quiet" onClick={() => setVisible((value) => !value)}>
        {visible ? `Ocultar ${revealLabel}` : `Mostrar ${revealLabel}`}
      </Button>
    </div>
    {hint ? <small>{hint}</small> : null}
  </div>;
}
