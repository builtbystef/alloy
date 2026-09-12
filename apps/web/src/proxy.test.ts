import { NextRequest } from "next/server";
import { describe, expect, test } from "vite-plus/test";

import { config, proxy } from "./proxy";

const ORIGIN = "http://localhost:3000";

function request(path: string, { session = false } = {}) {
  return new NextRequest(ORIGIN + path, {
    headers: session ? { cookie: "__Host-session=abc" } : {},
  });
}

function redirectedTo(response: Response): string | null {
  return response.status === 307 ? response.headers.get("location") : null;
}

describe("without a session", () => {
  test("app pages redirect to login, carrying the whole location as next", () => {
    expect(redirectedTo(proxy(request("/ws1/tasks?due=today")))).toBe(
      `${ORIGIN}/login?next=${encodeURIComponent("/ws1/tasks?due=today")}`,
    );
    expect(redirectedTo(proxy(request("/invites/tok")))).toBe(
      `${ORIGIN}/login?next=%2Finvites%2Ftok`,
    );
    // The home page needs no next: it is where login lands anyway.
    expect(redirectedTo(proxy(request("/")))).toBe(`${ORIGIN}/login`);
  });

  test("login, signup, and the open pages are served", () => {
    for (const path of [
      "/login",
      "/signup/",
      "/verify-email",
      "/reset-password?token=x",
      "/logout",
    ]) {
      expect(redirectedTo(proxy(request(path)))).toBeNull();
    }
  });
});

describe("with a session", () => {
  test("app pages and open pages are served", () => {
    for (const path of ["/", "/ws1/contacts", "/confirm-email?token=x", "/logout"]) {
      expect(redirectedTo(proxy(request(path, { session: true })))).toBeNull();
    }
  });

  test("login and signup go home instead", () => {
    expect(redirectedTo(proxy(request("/login?next=%2Fws1", { session: true })))).toBe(
      `${ORIGIN}/`,
    );
    expect(redirectedTo(proxy(request("/signup", { session: true })))).toBe(`${ORIGIN}/`);
  });
});

test("the API proxy, Next internals, and files are left to their handlers", () => {
  const [matcher] = config.matcher;
  const pattern = new RegExp(`^${matcher}$`);
  expect(pattern.test("/ws1/contacts")).toBe(true);
  expect(pattern.test("/login")).toBe(true);
  expect(pattern.test("/api/contacts/")).toBe(false);
  expect(pattern.test("/_next/static/chunk.js")).toBe(false);
  expect(pattern.test("/favicon.ico")).toBe(false);
  expect(pattern.test("/robots.txt")).toBe(false);
});
