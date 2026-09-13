import type { TaskRead } from "@alloy/api-client";

import type { EntityOption } from "@/components/shared/entity-combobox";

/**
 * A task links to a contact or a company, not both, so the form has one
 * "related to" picker over both lists. Its value is a key of the shape
 * `contact:<id>` or `company:<id>`, or "" for none; the API body gets the two
 * ids the key stands for.
 */

export const linkKinds = ["contact", "company"] as const;
export type LinkKind = (typeof linkKinds)[number];
export type LinkKey = `${LinkKind}:${string}`;

export interface TaskLink {
  contact_id?: string | null | undefined;
  company_id?: string | null | undefined;
}

export function linkKey(link: TaskLink | undefined): LinkKey | "" {
  if (link?.contact_id) return `contact:${link.contact_id}`;
  if (link?.company_id) return `company:${link.company_id}`;
  return "";
}

export function parseLinkKey(key: LinkKey | null): {
  contact_id: string | null;
  company_id: string | null;
} {
  if (key === null) return { contact_id: null, company_id: null };
  const [kind, id] = splitLinkKey(key);
  return kind === "contact"
    ? { contact_id: id, company_id: null }
    : { contact_id: null, company_id: id };
}

export function splitLinkKey(key: LinkKey): [LinkKind, string] {
  const at = key.indexOf(":");
  return [key.slice(0, at) as LinkKind, key.slice(at + 1)];
}

/** The picker option for a task's link, from the record the edit form holds. */
export function taskLinkOption(task: TaskRead): EntityOption | null {
  // `company` is set for a contact task too (it is the contact's), so contact first.
  if (task.contact) return { id: `contact:${task.contact.id}`, name: task.contact.name };
  if (task.company) return { id: `company:${task.company.id}`, name: task.company.name };
  return null;
}
