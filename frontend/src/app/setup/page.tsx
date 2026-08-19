import { redirect } from "next/navigation";

import { isInstallationInitialized } from "@/lib/setup";

import { SetupForm } from "./setup-form";

export default async function SetupPage() {
  if (await isInstallationInitialized()) redirect("/login");
  return (
    <main className="setup-shell">
      <header className="setup-header">
        <p className="eyebrow">Primer inicio</p>
        <h1>Configura tu espacio</h1>
        <p>Estos datos crean la organización y su primer propietario. Después, este asistente quedará cerrado.</p>
      </header>
      <section className="setup-card"><SetupForm /></section>
    </main>
  );
}
