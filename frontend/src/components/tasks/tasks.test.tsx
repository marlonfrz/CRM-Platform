import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { Task, TaskOptions, parseTaskFilters, taskApiQuery, taskFormBody, taskPageQuery } from "@/lib/tasks";
import { TaskForm } from "./TaskForm";
import { TaskEntry } from "./TaskEntry";
import { TasksPanel } from "./TasksPanel";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }) }));
const options: TaskOptions = {
  individual: false, departments: [{ id: "a", name: "Informática" }, { id: "b", name: "Marketing" }],
  candidates: [{ id: "ana", name: "Ana", department_ids: ["a"] }, { id: "bea", name: "Bea", department_ids: ["b"] }],
};
const task: Task = {
  id: "task", client_id: "client", client_name: "Hotel", title: "Llamar al cliente", description: "Revisar formulario",
  assigned_to_user_id: "ana", assigned_to_name: "Ana", created_by_user_id: "admin",
  department_id: "a", department_name: "Informática", due_at: null, status: "PENDING", completed_at: null,
  created_at: "2026-09-07T12:00:00Z", updated_at: "2026-09-07T12:00:00Z",
};

describe("Tasks", () => {
  it("individual creation has no visible department or assignee selectors and an optional due date", () => {
    const individual = { individual: true, departments: [], candidates: [{ id: "owner", name: "Owner", department_ids: [] }] };
    const markup = renderToStaticMarkup(<TaskForm clientId="client" options={individual} onDone={() => {}} />);
    expect(markup).not.toContain("<select");
    expect(markup).not.toContain("Departamento:");
    expect(markup).toContain('name="dueAt"');
    expect(markup).not.toMatch(/name="dueAt"[^>]*required/);
    expect(markup).toContain("Crear tarea");
  });

  it("requires a department when there are multiple and filters assignees on edit", () => {
    const create = renderToStaticMarkup(<TaskForm clientId="client" options={options} onDone={() => {}} />);
    expect(create).toContain('name="department" required=""');
    const edit = renderToStaticMarkup(<TaskForm clientId="client" task={task} options={options} onDone={() => {}} />);
    expect(edit).not.toContain('<select class="_select');
    expect(edit).not.toContain('name="department"');
    expect(edit).toContain("Ana");
    expect(edit).not.toContain(">Bea<");
  });

  it("preserves an unavailable current assignee while allowing a valid replacement", () => {
    const markup = renderToStaticMarkup(<TaskForm clientId="client" task={{ ...task, assigned_to_user_id: "old", assigned_to_name: "Anterior" }} options={options} onDone={() => {}} />);
    expect(markup).toContain("Anterior (responsable actual)");
    expect(markup).toContain('<option value="ana">Ana</option>');
  });

  it("shows due-less tasks and actions only for pending tasks", () => {
    const markup = renderToStaticMarkup(<TaskEntry task={task} options={options} />);
    expect(markup).toContain("Sin fecha límite");
    expect(markup).toContain("Completar tarea");
    expect(markup).toContain("Editar tarea");
    const completed = renderToStaticMarkup(<TaskEntry task={{ ...task, status: "COMPLETED", completed_at: "2026-09-07T13:00:00Z" }} options={options} />);
    expect(completed).toContain("Completada:");
    expect(completed).not.toContain("Completar tarea");
    expect(completed).not.toContain("Editar tarea");
    expect(completed).not.toContain("Eliminar");
  });

  it("my tasks link to their client and permit completion without a duplicate editing form", () => {
    const markup = renderToStaticMarkup(<TaskEntry task={task} options={null} />);
    expect(markup).toContain('href="/clients/client?tracking_filter=TASK_PENDING#tracking"');
    expect(markup).toContain("Completar tarea");
    expect(markup).not.toContain("Editar tarea");
  });

  it("paginates independently of activity filters and renders the empty state", () => {
    const markup = renderToStaticMarkup(<TasksPanel clientId="client"
      page={{ items: [], options: { ...options, candidates: [] }, has_more: true }}
      filters={{ status: "PENDING", offset: 20 }} preservedQuery="activity_type=NOTE&offset=40" />);
    expect(markup).toContain("No hay tareas visibles");
    expect(markup).not.toContain("Nueva tarea");
    expect(markup).toContain("activity_type=NOTE&amp;offset=40&amp;task_offset=40&amp;task_status=PENDING#tasks");
  });

  it("renders pending tasks before completed tasks", () => {
    const completed = { ...task, id: "completed", title: "Completed task", status: "COMPLETED" as const };
    const pending = { ...task, id: "pending", title: "Pending task" };
    const markup = renderToStaticMarkup(<TasksPanel
      page={{ items: [completed, pending], options, has_more: false }}
      filters={{ status: "", offset: 0 }}
    />);
    expect(markup.indexOf("Pending task")).toBeLessThan(markup.indexOf("Completed task"));
  });

  it("normalizes filters and serializes only accepted API fields", () => {
    expect(parseTaskFilters({ task_status: "INVALID", task_offset: "-1" })).toEqual({ status: "", offset: 0 });
    expect(taskApiQuery(parseTaskFilters({ task_status: "PENDING", task_offset: "20" }))).toBe("offset=20&status=PENDING");
    expect(taskPageQuery({ status: "COMPLETED", offset: 0 }, "activity_type=CALL")).toContain("activity_type=CALL");
    const data = new FormData();
    data.set("title", "  Call  "); data.set("department", "a"); data.set("assignee", "ana");
    expect(taskFormBody(data, false)).toEqual({ title: "Call", description: null, due_at: null, assigned_to_user_id: "ana", department_id: "a" });
    data.set("dueAt", "2026-10-01T10:30");
    const edit = taskFormBody(data, true);
    expect(edit).not.toHaveProperty("department_id");
    expect(edit.due_at).toBe("2026-10-01T10:30:00.000Z");
    expect(edit).not.toHaveProperty("status");
  });
});
