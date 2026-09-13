import { getToolName, isToolUIPart } from "ai";

import type { ChatMessage, ChatToolPart } from "./types";

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

/** The past tense of each label's first word, for a call that has finished. */
const finished: Record<string, string> = {
  Searching: "Searched",
  Reading: "Read",
  Creating: "Created",
  Updating: "Updated",
  Deleting: "Deleted",
  Logging: "Logged",
  Attaching: "Attached",
};

/**
 * What a tool call is shown as: "Searching contacts" while it runs, "Searched
 * contacts" once it is done. Falls back to the tool name.
 */
export function toolLabel(name: string, options: { done?: boolean } = {}): string {
  const label = labels[name] ?? name.replaceAll("_", " ");
  if (!options.done) return label;
  const [verb, ...rest] = label.split(" ");
  const past = verb === undefined ? undefined : finished[verb];
  return past ? [past, ...rest].join(" ") : label;
}

/** Worded like the API's own preview titles, for when a paused call has none. */
const writes: Record<string, { verb: string; one: string; many: string }> = {
  create_contacts: { verb: "Create", one: "contact", many: "contacts" },
  update_contacts: { verb: "Update", one: "contact", many: "contacts" },
  delete_contacts: { verb: "Delete", one: "contact", many: "contacts" },
  create_companies: { verb: "Create", one: "company", many: "companies" },
  update_companies: { verb: "Update", one: "company", many: "companies" },
  delete_companies: { verb: "Delete", one: "company", many: "companies" },
  log_activities: { verb: "Log", one: "activity", many: "activities" },
  create_tasks: { verb: "Create", one: "task", many: "tasks" },
  update_tasks: { verb: "Update", one: "task", many: "tasks" },
  delete_tasks: { verb: "Delete", one: "task", many: "tasks" },
  attach_files: { verb: "Attach", one: "file", many: "files" },
  delete_attachments: { verb: "Delete", one: "attachment", many: "attachments" },
};

export function approvalTitle(name: string, count: number | null): string {
  const write = writes[name];
  if (!write) {
    const label = toolLabel(name);
    return count === null ? label : `${label} (${count} ${count === 1 ? "item" : "items"})`;
  }
  if (count === null) return `${write.verb} ${write.many}`;
  return `${write.verb} ${count} ${count === 1 ? write.one : write.many}`;
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
