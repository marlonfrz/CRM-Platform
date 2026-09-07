"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { TextareaField } from "@/components/ui/TextareaField";
import { FormError, MutedText } from "@/components/ui/Text";
import type { Client, ClientContact } from "@/lib/clients";
import { apiRequest } from "@/lib/client-api";

import styles from "./client-detail-panel.module.css";

type ClientDetailPanelProps = {
  client: Client;
  canManage: boolean;
};

function nullableValue(formData: FormData, name: string) {
  const value = formData.get(name);
  return typeof value === "string" && value.trim() ? value : null;
}

function contactPayload(form: HTMLFormElement) {
  const formData = new FormData(form);
  return {
    full_name: formData.get("fullName"),
    position: nullableValue(formData, "position"),
    email: nullableValue(formData, "email"),
    phone: nullableValue(formData, "phone"),
    notes: nullableValue(formData, "notes"),
  };
}

export function ClientDetailPanel({ client, canManage }: ClientDetailPanelProps) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [editingClient, setEditingClient] = useState(false);
  const [editingContactId, setEditingContactId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function mutate(path: string, method: string, body?: object) {
    setError("");
    setSubmitting(true);
    const response = await apiRequest(path, {
      method,
      body: body ? JSON.stringify(body) : undefined,
    });
    setSubmitting(false);
    if (!response.ok) {
      setError(response.status === 403 ? "No tienes permiso para realizar esta acción." : "No se pudo guardar el cambio.");
      return false;
    }
    router.refresh();
    return true;
  }

  async function saveClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const saved = await mutate(`/clients/${client.id}`, "PATCH", {
      name: formData.get("name"),
      address: nullableValue(formData, "address"),
      notes: nullableValue(formData, "notes"),
    });
    if (saved) setEditingClient(false);
  }

  async function createContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (await mutate(`/clients/${client.id}/contacts`, "POST", contactPayload(form))) {
      form.reset();
    }
  }

  async function saveContact(event: FormEvent<HTMLFormElement>, contact: ClientContact) {
    event.preventDefault();
    if (
      await mutate(
        `/clients/${client.id}/contacts/${contact.id}`,
        "PATCH",
        contactPayload(event.currentTarget),
      )
    ) {
      setEditingContactId(null);
    }
  }

  async function removeContact(contact: ClientContact) {
    if (!window.confirm(`¿Eliminar a ${contact.full_name} de los contactos?`)) return;
    await mutate(`/clients/${client.id}/contacts/${contact.id}`, "DELETE");
  }

  return (
    <div className={styles.stack}>
      {error ? <FormError>{error}</FormError> : null}

      <Card className={styles.profileCard}>
        <div className={styles.sectionHeader}>
          <div>
            <span className={styles.sectionLabel}>Ficha general</span>
            <h2>Datos del cliente</h2>
          </div>
          {canManage && !editingClient ? (
            <Button type="button" variant="quiet" onClick={() => setEditingClient(true)}>
              Editar
            </Button>
          ) : null}
        </div>

        {editingClient ? (
          <form className={styles.formGrid} onSubmit={saveClient}>
            <FormField label="Nombre" name="name" defaultValue={client.name} required maxLength={200} />
            <FormField label="Dirección" name="address" defaultValue={client.address ?? ""} maxLength={500} />
            <TextareaField className={styles.fullWidth} label="Notas" name="notes" defaultValue={client.notes ?? ""} maxLength={5000} />
            <div className={`${styles.actions} ${styles.fullWidth}`}>
              <Button type="submit" disabled={submitting}>Guardar cambios</Button>
              <Button type="button" variant="quiet" onClick={() => setEditingClient(false)}>Cancelar</Button>
            </div>
          </form>
        ) : (
          <dl className={styles.details}>
            <div><dt>Nombre</dt><dd>{client.name}</dd></div>
            <div><dt>Dirección</dt><dd>{client.address || "Sin registrar"}</dd></div>
            <div className={styles.notes}><dt>Notas</dt><dd>{client.notes || "Sin notas"}</dd></div>
          </dl>
        )}
      </Card>

      {canManage ? (
        <Card className={styles.contactCreateCard}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.sectionLabel}>Nueva persona</span>
              <h2>Añadir contacto</h2>
            </div>
          </div>
          <form className={styles.formGrid} onSubmit={createContact}>
            <FormField label="Nombre completo" name="fullName" required maxLength={200} />
            <FormField label="Cargo" name="position" maxLength={200} />
            <FormField label="Email" name="email" type="email" maxLength={320} />
            <FormField label="Teléfono" name="phone" type="tel" maxLength={50} />
            <TextareaField className={styles.fullWidth} label="Notas" name="notes" maxLength={5000} />
            <div className={`${styles.actions} ${styles.fullWidth}`}>
              <Button type="submit" disabled={submitting}>{submitting ? "Guardando…" : "Añadir contacto"}</Button>
            </div>
          </form>
        </Card>
      ) : null}

      <section className={styles.contactsSection}>
        <div className={styles.contactsHeading}>
          <div>
            <span className={styles.sectionLabel}>Personas de contacto</span>
            <h2>Contactos</h2>
          </div>
          <span className={styles.count}>{client.contacts.length}</span>
        </div>

        {client.contacts.length ? (
          <div className={styles.contactsGrid}>
            {client.contacts.map((contact) => (
              <Card className={styles.contactCard} key={contact.id}>
                {editingContactId === contact.id ? (
                  <form className={styles.contactForm} onSubmit={(event) => saveContact(event, contact)}>
                    <FormField label="Nombre completo" name="fullName" defaultValue={contact.full_name} required maxLength={200} />
                    <FormField label="Cargo" name="position" defaultValue={contact.position ?? ""} maxLength={200} />
                    <FormField label="Email" name="email" type="email" defaultValue={contact.email ?? ""} maxLength={320} />
                    <FormField label="Teléfono" name="phone" type="tel" defaultValue={contact.phone ?? ""} maxLength={50} />
                    <TextareaField label="Notas" name="notes" defaultValue={contact.notes ?? ""} maxLength={5000} />
                    <div className={styles.actions}>
                      <Button type="submit" disabled={submitting}>Guardar</Button>
                      <Button type="button" variant="quiet" onClick={() => setEditingContactId(null)}>Cancelar</Button>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className={styles.contactIdentity}>
                      <span className={styles.avatar} aria-hidden="true">{contact.full_name.charAt(0).toUpperCase()}</span>
                      <div><h3>{contact.full_name}</h3><p>{contact.position || "Sin cargo registrado"}</p></div>
                    </div>
                    <div className={styles.contactMethods}>
                      {contact.email ? <a href={`mailto:${contact.email}`}>{contact.email}</a> : <MutedText>Sin email</MutedText>}
                      {contact.phone ? <a href={`tel:${contact.phone}`}>{contact.phone}</a> : <MutedText>Sin teléfono</MutedText>}
                    </div>
                    {contact.notes ? <p className={styles.contactNotes}>{contact.notes}</p> : null}
                    {canManage ? (
                      <div className={styles.actions}>
                        <Button type="button" variant="quiet" onClick={() => setEditingContactId(contact.id)}>Editar</Button>
                        <Button type="button" variant="danger" onClick={() => removeContact(contact)}>Eliminar</Button>
                      </div>
                    ) : null}
                  </>
                )}
              </Card>
            ))}
          </div>
        ) : (
          <div className={styles.empty}>
            <h3>Todavía no hay contactos</h3>
            <p>Añade las personas con las que se comunicará el equipo para este cliente.</p>
          </div>
        )}
      </section>
    </div>
  );
}
