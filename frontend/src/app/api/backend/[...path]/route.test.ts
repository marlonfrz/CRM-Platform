import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { GET, PATCH, POST } from "./route";

describe("backend proxy", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

  it("forwards the query string to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json([]));
    vi.stubGlobal("fetch", fetchMock);

    const request = new NextRequest(
      "http://localhost:3000/api/backend/ai/summaries/latest?scope=ORGANIZATION&client_id=example",
    );
    const response = await GET(request, {
      params: Promise.resolve({ path: ["ai", "summaries", "latest"] }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledOnce();
    const upstreamUrl = fetchMock.mock.calls[0][0] as URL;
    expect(upstreamUrl.pathname).toBe("/api/v1/ai/summaries/latest");
    expect(upstreamUrl.search).toBe("?scope=ORGANIZATION&client_id=example");
  });

  it("uses isolated synthetic state for demo writes without calling the backend", async () => {
    vi.stubEnv("DEMO_MODE", "true");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const context = { params: Promise.resolve({ path: ["clients"] }) };
    const create = await POST(new NextRequest("http://localhost:4173/api/backend/clients", {
      method: "POST", headers: { origin: "http://localhost:4173", host: "localhost:4173", "content-type": "application/json" },
      body: JSON.stringify({ name: "Nuevo cliente", address: "Calle 1", notes: "Nota sintética" }),
    }), context);
    expect(create.status).toBe(201);
    const client = await create.json() as { id: string };
    const cookie = create.headers.get("set-cookie")?.split(";")[0];
    expect(cookie).toContain("crm_demo_session=");
    const update = await PATCH(new NextRequest(`http://localhost:4173/api/backend/clients/${client.id}`, {
      method: "PATCH", headers: { cookie: cookie!, origin: "http://localhost:4173", host: "localhost:4173", "content-type": "application/json" },
      body: JSON.stringify({ name: "Cliente editado", address: "Calle 2", notes: "Nota actualizada" }),
    }), { params: Promise.resolve({ path: ["clients", client.id] }) });
    expect(update.status).toBe(200);
    const saved = await GET(new NextRequest(`http://localhost:4173/api/backend/clients/${client.id}`, {
      headers: { cookie: cookie! },
    }), { params: Promise.resolve({ path: ["clients", client.id] }) });
    expect((await saved.json()).address).toBe("Calle 2");
    const otherSession = await GET(new NextRequest(`http://localhost:4173/api/backend/clients/${client.id}`),
      { params: Promise.resolve({ path: ["clients", client.id] }) });
    expect(otherSession.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("creates recurring demo activities and deletes future occurrences", async () => {
    vi.stubEnv("DEMO_MODE", "true");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const clientId = "30000000-0000-4000-8000-000000000001";
    const path = ["clients", clientId, "activities"];
    const create = await POST(new NextRequest(`http://localhost:4173/api/backend/${path.join("/")}`, {
      method: "POST", headers: { origin: "http://localhost:4173", host: "localhost:4173", "content-type": "application/json" },
      body: JSON.stringify({ title: "Revisión semanal", description: "Comprobar reservas", status: "PENDING",
        department_id: "20000000-0000-4000-8000-000000000001",
        assigned_to_user_id: "10000000-0000-4000-8000-000000000003",
        scheduled_for: "2026-10-01", recurrence: { repeat_unit: "WEEK", repeat_interval: 1, weekdays: [3] } }),
    }), { params: Promise.resolve({ path }) });
    expect(create.status).toBe(201);
    const created = await create.json() as { id: string; ids: string[] };
    expect(created.ids).toHaveLength(2);
    expect(created.id).toBe(created.ids[0]);
    const cookie = create.headers.get("set-cookie")?.split(";")[0];
    const listed = await GET(new NextRequest(`http://localhost:4173/api/backend/${path.join("/")}`, {
      headers: { cookie: cookie! },
    }), { params: Promise.resolve({ path }) });
    const items = (await listed.json()).items as { id: string; schedule_id: string; scheduled_for: string }[];
    const first = items.find((item) => item.id === created.ids[0]);
    const second = items.find((item) => item.id === created.ids[1]);
    expect(second?.scheduled_for).toBe("2026-10-08");
    expect(first?.schedule_id).toBe(second?.schedule_id);
    const deletionPath = [...path, created.id];
    const { DELETE } = await import("./route");
    const deletion = await DELETE(new NextRequest(`http://localhost:4173/api/backend/${deletionPath.join("/")}?scope=THIS_AND_FOLLOWING`, {
      method: "DELETE", headers: { origin: "http://localhost:4173", host: "localhost:4173", cookie: cookie! },
    }), { params: Promise.resolve({ path: deletionPath }) });
    expect(deletion.status).toBe(204);
    const remaining = await GET(new NextRequest(`http://localhost:4173/api/backend/${path.join("/")}`, {
      headers: { cookie: cookie! },
    }), { params: Promise.resolve({ path }) });
    expect((await remaining.json()).items).not.toEqual(expect.arrayContaining([expect.objectContaining({ schedule_id: first?.schedule_id })]));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
