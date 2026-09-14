import { expect, test } from "vite-plus/test";

import { isInviteLink, safeNextPath, workspacePaths } from "./routes";

test("workspace paths all live under the workspace id", () => {
  const paths = workspacePaths("ws1");
  expect(paths.home).toBe("/ws1");
  expect(paths.contact("c1")).toBe("/ws1/contacts/c1");
  expect(paths.contactEdit("c1")).toBe("/ws1/contacts/c1/edit");
  expect(paths.task("t1")).toBe("/ws1/tasks/t1");
  expect(paths.taskEdit("t1")).toBe("/ws1/tasks/t1/edit");
  expect(paths.assistantChat("chat")).toBe("/ws1/assistant/chat");
  for (const value of Object.values(paths)) {
    const href = typeof value === "function" ? value("x") : value;
    expect(href.startsWith("/ws1")).toBe(true);
  }
});

test("a next path is kept only when it stays on this site", () => {
  expect(safeNextPath("/ws1/contacts?q=ada")).toBe("/ws1/contacts?q=ada");
  expect(safeNextPath("/invites/abc")).toBe("/invites/abc");
  expect(safeNextPath(null)).toBe("/");
  expect(safeNextPath(undefined)).toBe("/");
  expect(safeNextPath("")).toBe("/");
  expect(safeNextPath("https://evil.example/")).toBe("/");
  expect(safeNextPath("//evil.example/")).toBe("/");
  expect(safeNextPath("/\\evil.example/")).toBe("/");
  expect(safeNextPath("evil.example")).toBe("/");
});

test("an invite link is /invites/ plus a token, not the /invites list", () => {
  expect(isInviteLink("/invites/abc")).toBe(true);
  expect(isInviteLink("/invites/abc?x=1")).toBe(true);
  expect(isInviteLink("/invites")).toBe(false);
  expect(isInviteLink("/invites/")).toBe(false);
  expect(isInviteLink("/ws1/invites/abc")).toBe(false);
});
