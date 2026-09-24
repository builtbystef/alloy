import { createApiClient, type ImportResponse } from "@alloy/api-client";
import { expect, test, vi } from "vite-plus/test";

import { importKeys, importListQuery, isImportActive } from "./queries";

function record(status: ImportResponse["status"]): ImportResponse {
  return { status } as ImportResponse;
}

test("an import is active while queued or running", () => {
  expect(isImportActive(record("queued"))).toBe(true);
  expect(isImportActive(record("running"))).toBe(true);
  expect(isImportActive(record("pending"))).toBe(false);
  expect(isImportActive(record("done"))).toBe(false);
  expect(isImportActive(record("failed"))).toBe(false);
});

test("the list polls only while something is running", () => {
  const api = createApiClient({ baseUrl: "http://api.test" });
  const options = importListQuery(api, "ws1", 2);
  expect(options.queryKey).toEqual(["imports", "ws1", "list", 2]);
  expect(importKeys.lists("ws1")).toEqual(["imports", "ws1", "list"]);
  const interval = options.refetchInterval;
  if (typeof interval !== "function") throw new Error("expected a function");
  const query = (items: ImportResponse[] | undefined) =>
    ({
      state: { data: items ? { items, total: items.length, limit: 50, offset: 0 } : undefined },
    }) as never;
  expect(interval(query([record("done"), record("running")]))).toBe(2000);
  expect(interval(query([record("done"), record("failed")]))).toBe(false);
  expect(interval(query(undefined))).toBe(false);
});

test("the list asks the API for the page's rows", async () => {
  const fetch = vi.fn<typeof globalThis.fetch>(async () =>
    Response.json({ items: [], total: 0, limit: 50, offset: 50 }),
  );
  const api = createApiClient({ baseUrl: "http://api.test", fetch });
  const page = await importListQuery(api, "ws1", 2).queryFn!({} as never);
  expect(page.total).toBe(0);
  const request = fetch.mock.calls[0]?.[0] as Request;
  expect(request.url).toBe("http://api.test/workspaces/ws1/imports/?limit=50&offset=50");
});
