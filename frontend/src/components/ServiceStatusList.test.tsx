import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ServiceStatusList } from "./ServiceStatusList";

afterEach(cleanup);

describe("ServiceStatusList", () => {
  it("shows a text label for every state, not just a colour", () => {
    render(
      <ServiceStatusList
        statuses={[
          { name: "user-service", state: "ready", checks: { database: "ok" }, latencyMs: 12 },
          { name: "catalog-service", state: "not_ready", checks: { database: "unreachable" }, latencyMs: 30 },
          { name: "recommendation-service", state: "unreachable", checks: {}, latencyMs: null },
        ]}
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]).getByText("Ready")).toBeDefined();
    expect(within(items[0]).getByText("12 ms")).toBeDefined();
    expect(within(items[1]).getByText("Not ready")).toBeDefined();
    expect(within(items[1]).getByText("unreachable")).toBeDefined();
    expect(within(items[2]).getByText("Unreachable")).toBeDefined();
    expect(within(items[2]).queryByText(/ms$/)).toBeNull();
  });
});
