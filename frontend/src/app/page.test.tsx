import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("renders the project name", () => {
    const markup = renderToStaticMarkup(<HomePage />);

    expect(markup).toContain("CRM Platform");
  });
});
