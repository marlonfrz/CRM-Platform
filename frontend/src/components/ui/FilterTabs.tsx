import Link from "next/link";
import { MutedText } from "./Text";
import styles from "./FilterTabs.module.css";

export type FilterTab<T extends string> = { value: T; label: string; href?: string };

type Props<T extends string> = {
  items: FilterTab<T>[];
  activeValue: T;
  label: string;
  description: string;
  disabled?: boolean;
  onSelect?: (value: T) => void;
};

export function FilterTabs<T extends string>({
  items, activeValue, label, description, disabled = false, onSelect,
}: Props<T>) {
  return <div className={styles.group}>
    <nav className={styles.tabs} aria-label={label}>
      {items.map((item) => {
        const active = activeValue === item.value;
        const className = `${styles.tab} ${active ? styles.active : ""}`;
        return item.href ? <Link key={item.value || "ALL"} className={className}
          aria-current={active ? "page" : undefined} href={item.href}>{item.label}</Link>
          : <button key={item.value || "ALL"} className={className} type="button"
            aria-pressed={active} disabled={disabled} onClick={() => onSelect?.(item.value)}>{item.label}</button>;
      })}
    </nav>
    <MutedText>{description}</MutedText>
  </div>;
}
