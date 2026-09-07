import type { TextareaHTMLAttributes } from "react";

import styles from "./TextareaField.module.css";

type TextareaFieldProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  hint?: string;
};

export function TextareaField({ label, hint, ...textareaProps }: TextareaFieldProps) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      <textarea className={styles.textarea} {...textareaProps} />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}
