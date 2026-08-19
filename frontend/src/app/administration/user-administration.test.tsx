import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { UserAdministration } from "./user-administration";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("UserAdministration", () => {
  it("renders user status, role and department", () => {
    const markup = renderToStaticMarkup(
      <UserAdministration
        actorRole="OWNER"
        currentUserId="owner"
        departments={[{ id: "sales", name: "Ventas" }]}
        users={[{
          id: "employee",
          email: "employee@example.com",
          full_name: "Employee",
          role: "EMPLOYEE",
          status: "PENDING",
          department_ids: ["sales"],
        }]}
      />,
    );

    expect(markup).toContain("Invitación pendiente");
    expect(markup).toContain("Ventas");
    expect(markup).toContain("Reenviar");
  });
});
