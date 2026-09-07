import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import type { ClientSummary } from "@/lib/clients";
import { loadWorkspace, serverApi } from "@/lib/workspace";

import { ClientCreateForm } from "./client-create-form";
import styles from "./page.module.css";

type ClientsPageProps = {
  searchParams: Promise<{ search?: string }>;
};

export default async function ClientsPage({ searchParams }: ClientsPageProps) {
  const workspace = await loadWorkspace();
  const search = (await searchParams).search?.trim().slice(0, 200) ?? "";
  const path = search ? `/clients?search=${encodeURIComponent(search)}` : "/clients";
  const clients = await serverApi<ClientSummary[]>(path);
  const canManage = workspace.user_role !== "EMPLOYEE";

  return (
    <AppShell active="clients" workspace={workspace}>
      <header className={styles.header}>
        <Eyebrow>Clientes</Eyebrow>
        <h1>{canManage ? "Clientes" : "Mis clientes"}</h1>
        <MutedText>{canManage ? "Una ficha única por cliente para toda la organización." : "Consulta los clientes que tienes asignados y sus contactos."}</MutedText>
      </header>

      <div className={styles.stack}>
        {canManage ? <ClientCreateForm /> : null}

        <Card className={styles.directory}>
          <div className={styles.directoryHeader}>
            <div>
              <h2>Directorio</h2>
              <MutedText>{clients.length === 1 ? "1 cliente" : `${clients.length} clientes`}</MutedText>
            </div>
            <form className={styles.search} method="get">
              <FormField
                aria-label="Buscar clientes"
                label="Buscar por nombre"
                name="search"
                defaultValue={search}
                maxLength={200}
              />
              <Button type="submit" variant="quiet">Buscar</Button>
              {search ? <Link className={styles.clear} href="/clients">Limpiar</Link> : null}
            </form>
          </div>

          {clients.length ? (
            <div className={styles.clientGrid}>
              {clients.map((client) => (
                <Link className={styles.clientLink} href={`/clients/${client.id}`} key={client.id}>
                  <article className={styles.clientCard}>
                    <div>
                      <span className={styles.clientLabel}>Cliente</span>
                      <h3>{client.name}</h3>
                    </div>
                    <p>{client.address || "Sin dirección registrada"}</p>
                    <span className={styles.open}>Ver ficha <span aria-hidden="true">→</span></span>
                  </article>
                </Link>
              ))}
            </div>
          ) : (
            <div className={styles.empty}>
              <h3>{search ? "No hay coincidencias" : "Todavía no hay clientes"}</h3>
              <p>
                {workspace.user_role === "EMPLOYEE"
                  ? "Tus clientes aparecerán aquí cuando te los asignen."
                  : search
                    ? "Prueba con otro nombre o limpia la búsqueda."
                    : "Crea la primera ficha desde el formulario superior."}
              </p>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
