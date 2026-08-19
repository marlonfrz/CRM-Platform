import type { InputHTMLAttributes } from "react";

import styles from "./FormField.module.css";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
};

export function FormField({ label, hint, ...inputProps }: FormFieldProps) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      <input className={styles.input} {...inputProps} />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}
