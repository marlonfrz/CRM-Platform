import { Card } from "@/components/ui/Card";
import styles from "./MetricCard.module.css";

export function MetricCard({ label, value }: { label: string; value: number }) {
  return <Card className={styles.card}><span>{label}</span><strong>{value.toLocaleString("es-ES")}</strong></Card>;
}
