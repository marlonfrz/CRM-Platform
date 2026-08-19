import type { HTMLAttributes } from "react";

import styles from "./Text.module.css";

export function Eyebrow(props: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={styles.eyebrow} {...props} />;
}

export function MutedText({ className = "", ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={`${styles.muted} ${className}`} {...props} />;
}

export function FormError(props: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={styles.error} role="alert" {...props} />;
}
