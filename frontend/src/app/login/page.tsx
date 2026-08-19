import { redirect } from "next/navigation";

import { isInstallationInitialized } from "@/lib/setup";

import { LoginForm } from "./login-form";

export default async function LoginPage() {
  if (!(await isInstallationInitialized())) redirect("/setup");
  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <p className="eyebrow">CRM Platform</p>
        <h1>Tu trabajo comercial, en un único lugar.</h1>
        <p>Gestiona clientes, actividad y tareas con el contexto correcto para cada equipo.</p>
      </section>
      <section className="login-card">
        <p className="eyebrow">Acceso privado</p>
        <h2>Inicia sesión</h2>
        <p className="muted">Usa la cuenta configurada para esta instalación.</p>
        <LoginForm />
      </section>
    </main>
  );
}
