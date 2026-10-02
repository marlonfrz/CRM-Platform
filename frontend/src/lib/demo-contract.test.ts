import { describe, expect, it } from "vitest";

import { demoRead, demoWrite } from "./demo-store";

describe("Demo API contract", () => {
  it("uses neutral organization, client, contact and user names", async () => {
    const workspace = await demoRead("/workspace").json() as { organization_name: string };
    const clients = await demoRead("/clients").json() as { id: string; name: string }[];
    const users = await demoRead("/admin/users").json() as { full_name: string }[];

    expect(workspace.organization_name).toBe("Organización Ejemplo");
    expect(clients.map((client) => client.name)).toEqual(["Cliente Alfa", "Cliente Beta", "Cliente Gamma"]);
    expect(users.every((user) => user.full_name.startsWith("Usuario "))).toBe(true);
    for (const client of clients) {
      const detail = await demoRead(`/clients/${client.id}`).json() as { contacts: { full_name: string }[] };
      expect(detail.contacts.every((contact) => contact.full_name.startsWith("Contacto "))).toBe(true);
    }
  });

  it("returns the workspace and authenticated user shapes", async () => {
    const workspace = await demoRead("/workspace").json();
    const user = await demoRead("/auth/me").json();

    expect(workspace).toMatchObject({
      organization_id: expect.any(String),
      organization_name: expect.any(String),
      user_id: expect.any(String),
      departments: expect.any(Array),
    });
    expect(user).toEqual({
      id: workspace.user_id,
      organization_id: workspace.organization_id,
      email: workspace.user_email,
      full_name: workspace.user_name,
      role: workspace.user_role,
      status: "ACTIVE",
    });
  });

  it("exposes activity types and date-only task deadlines", async () => {
    const clients = await demoRead("/clients").json();
    const clientId = clients[0].id;
    const activities = await demoRead(`/clients/${clientId}/activities?period=TODAY`).json();
    const tasks = await demoRead(`/clients/${clientId}/tasks`).json();

    expect(activities.items.length).toBeGreaterThan(0);
    expect(activities.items[0]).toMatchObject({ type: expect.any(String) });
    expect(tasks.items.length).toBeGreaterThan(0);
    expect(tasks.items[0].due_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("uses the same creation response shapes as the backend", async () => {
    const clients = await demoRead("/clients").json();
    const clientId = clients[0].id;
    const activities = await demoRead(`/clients/${clientId}/activities?period=TODAY`).json();
    const reference = activities.items[0];
    const payload = {
      activity_type_id: reference.activity_type_id,
      department_id: reference.department_id,
      assigned_to_user_id: reference.assigned_to_user_id,
      description: "Verificar contrato de la demo",
      status: "PENDING",
      scheduled_for: reference.scheduled_for,
    };

    const activity = await demoWrite(`/clients/${clientId}/activities`, "POST", payload);
    expect(activity.response.status).toBe(201);
    expect(await activity.response.json()).toMatchObject({ id: expect.any(String), ids: [expect.any(String)] });

    const task = await demoWrite(`/clients/${clientId}/tasks`, "POST", {
      title: "Revisar tarea", description: null, due_at: `${reference.scheduled_for}T12:00:00Z`,
      department_id: reference.department_id, assigned_to_user_id: reference.assigned_to_user_id,
    });
    expect(task.response.status).toBe(201);
    expect(await task.response.json()).toEqual({ id: expect.any(String) });
  });
});
