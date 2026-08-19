import { redirect } from "next/navigation";

import { isInstallationInitialized } from "@/lib/setup";
import { Card } from "@/components/ui/Card";
import { Eyebrow, MutedText } from "@/components/ui/Text";

import { SetupForm } from "./setup-form";
import styles from "./page.module.css";

export default async function SetupPage() {
  if (await isInstallationInitialized()) redirect("/login");
  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <Eyebrow>Primer inicio</Eyebrow>
        <h1>Configura tu espacio</h1>
        <MutedText className={styles.description}>Estos datos crean la organización y su primer propietario. Después, este asistente quedará cerrado.</MutedText>
      </header>
      <Card className={styles.card}><SetupForm /></Card>
    </main>
  );
}
