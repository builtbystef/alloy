import { expect, test } from "vite-plus/test";

import type { ChatMessage, ChatToolPart } from "./types";
import { approvalTitle, changedRecords, isWriteTool, toolLabel, toolParts } from "./tools";

function toolPart(name: string, state: ChatToolPart["state"]): ChatToolPart {
  return { type: `tool-${name}`, toolCallId: "c1", state, input: {}, output: {} } as ChatToolPart;
}

function message(parts: ChatMessage["parts"]): ChatMessage {
  return { id: "m1", role: "assistant", parts };
}

test("tool labels are readable, with a fallback for unknown tools", () => {
  expect(toolLabel("search_contacts")).toBe("Searching contacts");
  expect(toolLabel("get_workspace")).toBe("Reading the workspace");
  expect(toolLabel("some_new_tool")).toBe("some new tool");
});

test("write tools are the ones that change records", () => {
  for (const name of [
    "create_contacts",
    "update_tasks",
    "delete_companies",
    "log_activities",
    "attach_files",
  ]) {
    expect(isWriteTool(name)).toBe(true);
  }
  for (const name of ["search_contacts", "get_contact", "list_tasks", "get_workspace"]) {
    expect(isWriteTool(name)).toBe(false);
  }
});

test("records changed only when a write tool finished", () => {
  expect(changedRecords(message([toolPart("create_contacts", "output-available")]))).toBe(true);
  expect(changedRecords(message([toolPart("create_contacts", "approval-requested")]))).toBe(false);
  expect(changedRecords(message([toolPart("create_contacts", "output-denied")]))).toBe(false);
  expect(changedRecords(message([toolPart("create_contacts", "output-error")]))).toBe(false);
  expect(changedRecords(message([toolPart("search_contacts", "output-available")]))).toBe(false);
  expect(changedRecords(message([{ type: "text", text: "Done." }]))).toBe(false);
});

test("tool parts are picked out of a message", () => {
  const call = toolPart("list_tasks", "output-available");
  const parts = toolParts(
    message([{ type: "text", text: "Looking." }, call, { type: "step-start" }]),
  );
  expect(parts).toEqual([call]);
});

test("approval titles read like the API's previews", () => {
  expect(approvalTitle("create_contacts", 3)).toBe("Create 3 contacts");
  expect(approvalTitle("delete_contacts", 1)).toBe("Delete 1 contact");
  expect(approvalTitle("create_companies", 2)).toBe("Create 2 companies");
  expect(approvalTitle("log_activities", 1)).toBe("Log 1 activity");
  expect(approvalTitle("attach_files", 4)).toBe("Attach 4 files");
  expect(approvalTitle("update_tasks", null)).toBe("Update tasks");
  expect(approvalTitle("some_new_tool", 2)).toBe("some new tool (2 items)");
  expect(approvalTitle("some_new_tool", null)).toBe("some new tool");
});
