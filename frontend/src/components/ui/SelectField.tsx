import type { SelectHTMLAttributes } from "react";

import styles from "./SelectField.module.css";

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: { label: string; value: string }[];
};

export function SelectField({ label, options, ...selectProps }: SelectFieldProps) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      <select className={styles.select} {...selectProps}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}
