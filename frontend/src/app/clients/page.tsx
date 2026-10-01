import Link from "next/link";

import { AppShell } from "@/components/layout/AppShell";
import { HistoryItem } from "@/components/history/HistoryItem";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Eyebrow, MutedText } from "@/components/ui/Text";
import type { Client, ClientSummary } from "@/lib/clients";
import type { HistoryPage } from "@/lib/insights";
import { loadWorkspace, serverApi } from "@/lib/workspace";

import { ClientCreateForm } from "./client-create-form";
import styles from "./page.module.css";

type ClientsPageProps = {
  searchParams: Promise<{ search?: string; client?: string }>;
};

export default async function ClientsPage({ searchParams }: ClientsPageProps) {
  const workspace = await loadWorkspace();
  const query = await searchParams;
  const search = query.search?.trim().slice(0, 200) ?? "";
  const path = search ? `/clients?search=${encodeURIComponent(search)}` : "/clients";
  const clients = await serverApi<ClientSummary[]>(path);
  const selectedId = clients.some((client) => client.id === query.client)
    ? query.client
    : clients[0]?.id;
  const selectedClient = selectedId ? await serverApi<Client>(`/clients/${selectedId}`) : null;
  const selectedHistory = selectedId
    ? await serverApi<HistoryPage>(`/clients/${selectedId}/history?limit=5`)
    : null;
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

        <div className={styles.directory}>
          <Card className={styles.clientListPanel}>
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
            <div className={styles.clientList}>
              {clients.map((client) => (
                <Link className={`${styles.clientRow} ${client.id === selectedId ? styles.selectedClient : ""}`}
                  href={`/clients?${new URLSearchParams({ ...(search ? { search } : {}), client: client.id })}`}
                  key={client.id}>
                  <strong>{client.name}</strong>
                  <span>{client.address || "Sin dirección registrada"}</span>
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

          {selectedClient ? <Card className={styles.clientDetail}>
            <div className={styles.detailHeader}>
              <div><span className={styles.clientLabel}>Ficha de cliente</span><h2>{selectedClient.name}</h2>
                <p>{selectedClient.address || "Sin dirección registrada"}</p></div>
              <ButtonLink href={`/clients/${selectedClient.id}`} variant="quiet">Abrir ficha completa</ButtonLink>
            </div>
            <div className={styles.contactsHeading}><h3>Contactos</h3><span>{selectedClient.contacts.length} registrados</span></div>
            {selectedClient.contacts.length ? <div className={styles.contactGrid}>
              {selectedClient.contacts.map((contact) => <article className={styles.contactCard} key={contact.id}>
                <span>{contact.position || "Contacto"}</span><strong>{contact.full_name}</strong>
                {contact.email ? <a href={`mailto:${contact.email}`}>{contact.email}</a> : <MutedText>Sin email</MutedText>}
                {contact.phone ? <a href={`tel:${contact.phone}`}>{contact.phone}</a> : <MutedText>Sin teléfono</MutedText>}
              </article>)}
            </div> : <MutedText className={styles.compactEmpty}>Todavía no hay contactos registrados.</MutedText>}
            <div className={styles.trackingHeading}><h3>Seguimiento reciente</h3><span>{selectedHistory?.items.length ?? 0} registros</span></div>
            <div className={styles.trackingList}>
              {selectedHistory?.items.map((entry) => <HistoryItem key={entry.id} entry={entry} compact />)}
              {!selectedHistory?.items.length ? <MutedText className={styles.compactEmpty}>No hay actividad visible para este cliente.</MutedText> : null}
            </div>
          </Card> : null}
        </div>
      </div>
    </AppShell>
  );
}
