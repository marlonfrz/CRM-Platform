import { redirect } from "next/navigation";

import { isInstallationInitialized } from "@/lib/setup";
import { Card } from "@/components/ui/Card";
import { Eyebrow, MutedText } from "@/components/ui/Text";

import { LoginForm } from "./login-form";
import styles from "./page.module.css";

export default async function LoginPage() {
  if (process.env.DEMO_MODE === "true") redirect("/dashboard");
  if (!(await isInstallationInitialized())) redirect("/setup");
  return (
    <main className={styles.shell}>
      <section className={styles.brand}>
        <Eyebrow>CRM Platform</Eyebrow>
        <h1>Tu trabajo comercial, en un único lugar.</h1>
        <p className={styles.brandDescription}>Gestiona clientes, actividad y tareas con el contexto correcto para cada equipo.</p>
      </section>
      <Card className={styles.card}>
        <Eyebrow>Acceso privado</Eyebrow>
        <h2>Inicia sesión</h2>
        <MutedText>Usa la cuenta configurada para esta instalación.</MutedText>
        <LoginForm />
      </Card>
    </main>
  );
}
