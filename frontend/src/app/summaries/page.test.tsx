import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SummaryPanel } from "@/components/summaries/SummaryPanel";
import { LatestSummaries } from "@/components/summaries/LatestSummaries";
import { SummaryResult } from "@/components/summaries/SummaryResult";
import { SummaryOptions } from "@/lib/summaries";
import { defaultSummaryPeriod } from "@/lib/summary-period";
import { loadWorkspace, serverApi, Workspace } from "@/lib/workspace";
import SummariesPage from "./page";

vi.mock("@/lib/workspace", () => ({ loadWorkspace: vi.fn(), serverApi: vi.fn() }));
vi.mock("next/navigation", () => ({
  redirect: () => { throw new Error("REDIRECT"); },
  notFound: () => { throw new Error("NOT_FOUND"); },
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));
const workspace: Workspace = {
  organization_id: "organization", user_id: "owner", user_name: "Owner", user_email: "owner@example.com", user_role: "OWNER",
  organization_name: "Test", organization_mode: "BUSINESS", departments: [],
};
const options: SummaryOptions = {
  enabled: false, provider: "disabled", model: "", external: false,
  departments: [{ id: "department", name: "Sales" }],
};

describe("AI summaries", () => {
  beforeEach(() => {
    vi.mocked(loadWorkspace).mockReset().mockResolvedValue(workspace);
    vi.mocked(serverApi).mockReset().mockResolvedValue(options);
  });
  it("rejects employees before querying AI options", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: "EMPLOYEE" });
    await expect(SummariesPage({})).rejects.toThrow("REDIRECT");
    expect(serverApi).not.toHaveBeenCalled();
  });
  it("leaves generation disabled when no provider is configured", async () => {
    const markup = renderToStaticMarkup(await SummariesPage({}));
    const period = defaultSummaryPeriod();
    expect(markup).toContain('<fieldset disabled=""');
    expect(markup).toContain("Generar resumen");
    expect(markup).toContain('name="department_id"');
    expect(markup).not.toContain("Alcance");
    expect(markup).toContain(`value="${period.since}"`);
    expect(markup).toContain(`value="${period.until}"`);
    expect(markup).toContain("Opciones");
    expect(serverApi).toHaveBeenCalledExactlyOnceWith("/ai/options", { notFoundOnDenied: true });
  });
  it("does not offer global summaries to admins", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: "ADMIN" });
    const markup = renderToStaticMarkup(await SummariesPage({}));
    expect(markup).not.toContain("Toda la organización");
    expect(markup).not.toContain(">Opciones<");
    expect(markup).toContain('name="department_id"');
    expect(markup).toContain("Sales");
  });
  it("shows encrypted provider options only to the owner", async () => {
    vi.mocked(serverApi).mockResolvedValueOnce({
      provider: "anthropic", model: "claude-sonnet-5", has_api_key: true, source: "organization",
    });
    const markup = renderToStaticMarkup(await SummariesPage({
      searchParams: Promise.resolve({ view: "SETTINGS" }),
    }));
    expect(serverApi).toHaveBeenCalledExactlyOnceWith("/ai/configuration", { notFoundOnDenied: true });
    expect(markup).toContain("Opciones de IA");
    expect(markup).toContain("Anthropic (Claude API)");
    expect(markup).toContain("Claude Haiku 4.5");
    expect(markup).toContain("Claude Sonnet 5");
    expect(markup).not.toContain("Identificador avanzado");
    expect(markup).toContain("Token de API");
    expect(markup).not.toContain("claude-secret");

    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, user_role: "ADMIN" });
    await expect(SummariesPage({ searchParams: Promise.resolve({ view: "SETTINGS" }) }))
      .rejects.toThrow("REDIRECT");
  });
  it("omits department controls in individual mode", async () => {
    vi.mocked(loadWorkspace).mockResolvedValue({ ...workspace, organization_mode: "INDIVIDUAL" });
    const markup = renderToStaticMarkup(await SummariesPage({}));
    expect(markup).not.toContain('name="department_id"');
    expect(markup).not.toContain("Un departamento");
  });
  it("generates an external summary without a per-request checkbox or cost preview", () => {
    const markup = renderToStaticMarkup(<SummaryPanel options={{ ...options, enabled: true, external: true, provider: "openai", model: "test" }}
      individual={false} initialSince="2026-09-01T00:00" initialUntil="2026-09-09T00:00" />);
    expect(markup).toContain("Generar resumen");
    expect(markup).not.toContain('type="checkbox"');
    expect(markup).not.toContain("Calcular tokens y coste");
    expect(markup).not.toContain('<fieldset disabled=""');
  });
  it.each(["bad", "------------------------------------", ["a", "b"]])("rejects invalid client targets", async (client_id) => {
    await expect(SummariesPage({ searchParams: Promise.resolve({ client_id }) })).rejects.toThrow("NOT_FOUND");
    expect(serverApi).not.toHaveBeenCalled();
  });
  it("checks access to a client and fixes the summary scope", async () => {
    const clientId = "12345678-1234-1234-1234-123456789abc";
    vi.mocked(serverApi).mockResolvedValueOnce({ name: "Client A" }).mockResolvedValueOnce(options);
    const markup = renderToStaticMarkup(await SummariesPage({ searchParams: Promise.resolve({ client_id: clientId }) }));
    expect(serverApi).toHaveBeenNthCalledWith(1, `/clients/${clientId}`, { notFoundOnDenied: true });
    expect(markup).toContain("Resumen de Client A");
    expect(markup).not.toContain("Toda la organización");
  });
  it("renders untrusted model output only as escaped text", () => {
    const markup = renderToStaticMarkup(<SummaryResult result={{ request_id: "request", generated_at: "2026-09-09T10:00:00Z", provider: "ollama", model: "test", sections: [{
      department_id: null, department_name: null,
      content: { summary: "<script>alert(1)</script>", pending_actions: ["[click](https://attacker.test)"], source_ids: ["activity"] },
      sources: [{ id: "activity", client_id: "client", client_name: "Client A", activity_type_name: "Llamada",
        title: "Confirmar recepción", description: "<script>alert(2)</script>", status: "COMPLETED",
        scheduled_for: "2026-09-09", occurred_at: "2026-09-09T10:00:00Z" }],
    }] }} />);
    expect(markup).toContain("&lt;script&gt;");
    expect(markup).not.toContain("<script>");
    expect(markup).not.toContain('href="https://attacker.test"');
    expect(markup).toContain('href="/clients/client#tracking"');
    expect(markup).toContain("Confirmar recepción");
    expect(markup).toContain("Tipo: Llamada");
    expect(markup).toContain("Cliente: ");
    expect(markup).toContain("&lt;script&gt;alert(2)&lt;/script&gt;");
    expect(markup).not.toContain("ID: activity");
    expect(markup).toContain("Resumen personal");
    expect(markup).toContain("no son tareas creadas ni confirmadas");
  });
  it("explains empty contexts without inventing a summary", () => {
    const markup = renderToStaticMarkup(<SummaryResult result={{ request_id: null, generated_at: "2026-09-09T10:00:00Z", provider: "ollama", model: "test", sections: [] }} />);
    expect(markup).toContain("No se ha consultado la IA");
    expect(markup).toContain("No se ha hecho una nueva llamada al proveedor");
  });
  it("shows a boxed estimated cost from reported usage after generating", () => {
    const markup = renderToStaticMarkup(<SummaryResult result={{
      request_id: "request", generated_at: "2026-09-09T10:00:00Z", provider: "openai", model: "gpt-5.6-luna",
      usage: { input_tokens: 100, output_tokens: 200, estimated_cost_usd: 0.00026 }, sections: [{
        department_id: null, department_name: null,
        content: { summary: "Resumen", pending_actions: [], source_ids: ["activity"] },
        sources: [{ id: "activity", client_id: "client", client_name: "Cliente", activity_type_name: "Llamada",
          title: null, description: "Contacto realizado", status: "COMPLETED",
          scheduled_for: "2026-09-09", occurred_at: "2026-09-09T10:00:00Z" }],
      }],
    }} />);
    expect(markup).toContain('aria-label="Coste de la consulta"');
    expect(markup).toContain("Coste de esta consulta");
    expect(markup).toContain("0,00026");
    expect(markup).toContain("100 tokens de entrada · 200 de salida");
    expect(markup).toContain("Importe orientativo");
  });
  it("shows zero for cache hits and no invented cost for unknown tariffs", () => {
    const base = { request_id: "request", generated_at: "2026-09-09T10:00:00Z", provider: "openai", model: "custom", sections: [{
      department_id: null, department_name: null,
      content: { summary: "Resumen", pending_actions: [], source_ids: ["activity"] },
      sources: [{ id: "activity", client_id: "client", client_name: "Cliente", activity_type_name: "Llamada",
        title: null, description: "Contacto realizado", status: "COMPLETED" as const,
        scheduled_for: "2026-09-09", occurred_at: "2026-09-09T10:00:00Z" }],
    }] };
    const cached = renderToStaticMarkup(<SummaryResult result={{ ...base, cached: true }} />);
    expect(cached).toContain("0,0000");
    expect(cached).toContain("No se ha hecho una nueva llamada");
    const unknown = renderToStaticMarkup(<SummaryResult result={{ ...base, usage: { input_tokens: 12, output_tokens: 4, estimated_cost_usd: null } }} />);
    expect(unknown).toContain("No disponible");
    expect(unknown).toContain("tarifa verificada");
  });
  it("defaults to today through the same day next month, including month ends", () => {
    expect(defaultSummaryPeriod(new Date("2026-09-21T10:00:00Z"))).toEqual({
      since: "2026-09-21T00:00", until: "2026-10-21T23:59",
    });
    expect(defaultSummaryPeriod(new Date("2026-01-31T10:00:00Z"))).toEqual({
      since: "2026-01-31T00:00", until: "2026-02-28T23:59",
    });
  });
  it("shows a saved department summary with its generation and coverage dates", () => {
    const markup = renderToStaticMarkup(<LatestSummaries loading={false} error="" items={[{
      generated_at: "2026-09-21T10:00:00Z", since: "2026-09-21T00:00:00Z",
      until: "2026-10-21T23:59:00Z", provider: "openai", model: "test",
      section: { department_id: "department", department_name: "Diseño",
        content: { summary: "Plan de trabajo", pending_actions: [], source_ids: [] }, sources: [] },
    }]} />);
    expect(markup).toContain("Últimos resúmenes guardados");
    expect(markup).toContain("Periodo:");
    expect(markup).toContain("Generado:");
    expect(markup).toContain("Diseño");
    expect(markup).toContain("Plan de trabajo");
  });
  it("labels future source activities as scheduled rather than completed", () => {
    const markup = renderToStaticMarkup(<SummaryResult result={{
      request_id: "request", generated_at: "2026-09-21T10:00:00Z", provider: "ollama", model: "test",
      sections: [{ department_id: null, department_name: null,
        content: { summary: "Se ha previsto una llamada.", pending_actions: ["Llamar al cliente"], source_ids: ["activity"] },
        sources: [{ id: "activity", client_id: "client", client_name: "Cliente",
          activity_type_name: "Llamada", title: "Seguimiento", description: "Llamar al cliente",
          status: "PENDING", scheduled_for: "2026-10-01", occurred_at: null }],
      }],
    }} period={{ since: "2026-09-21T00:00:00Z", until: "2026-10-21T23:59:00Z" }} />);
    expect(markup).toContain("Programada:");
    expect(markup).toContain("Periodo:");
    expect(markup).not.toContain("Realizada:");
  });
});
