import { getToolName, isToolUIPart } from "ai";

import type { ChatMessage, ChatToolPart } from "./chat-types";

/** What each tool call is shown as while it runs. Falls back to the tool name. */
const labels: Record<string, string> = {
  search_contacts: "Searching contacts",
  get_contact: "Reading a contact",
  create_contacts: "Creating contacts",
  update_contacts: "Updating contacts",
  delete_contacts: "Deleting contacts",
  search_companies: "Searching companies",
  get_company: "Reading a company",
  create_companies: "Creating companies",
  update_companies: "Updating companies",
  delete_companies: "Deleting companies",
  list_activities: "Reading activities",
  log_activities: "Logging activities",
  list_tasks: "Reading tasks",
  create_tasks: "Creating tasks",
  update_tasks: "Updating tasks",
  delete_tasks: "Deleting tasks",
  list_attachments: "Reading attachments",
  attach_files: "Attaching files",
  delete_attachments: "Deleting attachments",
  get_workspace: "Reading the workspace",
  list_members: "Reading members",
};

export function toolLabel(name: string): string {
  return labels[name] ?? name.replaceAll("_", " ");
}

/** Tools that change records; a finished one means the CRM queries are stale. */
export function isWriteTool(name: string): boolean {
  return /^(create|update|delete|log|attach)_/.test(name);
}

/** Whether the assistant's reply ran a write that completed. */
export function changedRecords(message: ChatMessage): boolean {
  return message.parts.some(
    (part) =>
      isToolUIPart(part) && part.state === "output-available" && isWriteTool(getToolName(part)),
  );
}

export function toolParts(message: ChatMessage): ChatToolPart[] {
  return message.parts.filter((part): part is ChatToolPart => isToolUIPart(part));
}
