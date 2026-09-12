import { expect, test } from "vite-plus/test";

import {
  assignableRoles,
  canManageRole,
  roleDescriptions,
  roleLabels,
  workspaceRoles,
} from "./roles";

test("owners manage every role, others only the roles below their own", () => {
  expect(assignableRoles("owner")).toEqual(["owner", "admin", "member", "viewer"]);
  expect(assignableRoles("admin")).toEqual(["member", "viewer"]);
  expect(assignableRoles("member")).toEqual(["viewer"]);
  expect(assignableRoles("viewer")).toEqual([]);
  // Nobody but an owner touches an equal.
  expect(canManageRole("admin", "admin")).toBe(false);
  expect(canManageRole("owner", "owner")).toBe(true);
});

test("every role has a label and a description", () => {
  for (const role of workspaceRoles) {
    expect(roleLabels[role]).toBeTruthy();
    expect(roleDescriptions[role]).toBeTruthy();
  }
});
