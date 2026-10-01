import type { ButtonHTMLAttributes, ComponentProps } from "react";
import Link from "next/link";

import styles from "./Button.module.css";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet" | "danger";
};

type ButtonLinkProps = ComponentProps<typeof Link> & {
  variant?: ButtonProps["variant"];
};

export function Button({ className = "", variant = "primary", ...props }: ButtonProps) {
  return <button className={`${styles.button} ${styles[variant]} ${className}`} {...props} />;
}

export function ButtonLink({ className = "", variant = "primary", ...props }: ButtonLinkProps) {
  return <Link className={`${styles.button} ${styles.buttonLink} ${styles[variant]} ${className}`} {...props} />;
}
