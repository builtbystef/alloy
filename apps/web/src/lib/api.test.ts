import { afterEach, expect, test, vi } from "vite-plus/test";

import { createApi, getApiUrl } from "./api";

afterEach(() => {
  vi.unstubAllEnvs();
});

test("defaults to the local FastAPI dev server", () => {
  vi.stubEnv("API_URL", undefined);
  expect(getApiUrl()).toBe("http://127.0.0.1:8000");
});

test("API_URL overrides the base URL for every request", async () => {
  vi.stubEnv("API_URL", "https://api.example.test");
  const fetch = vi.fn<typeof globalThis.fetch>(async () => Response.json({ status: "ok" }));

  const { data } = await createApi(fetch).GET("/health/");

  expect(data).toEqual({ status: "ok" });
  const request = fetch.mock.calls[0]?.[0] as Request | undefined;
  expect(request?.url).toBe("https://api.example.test/health/");
});
