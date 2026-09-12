import type { ActivityType, ContactSort, ContactStatus } from "@alloy/api-client";
import { z } from "zod";

import { listSearch, optionalParam, parseSearch, type SearchParams } from "@/lib/lists";
import {
  optionalDateTime,
  optionalEmail,
  optionalId,
  optionalNotes,
  optionalText,
  requiredText,
  text,
} from "@/lib/validation";

export const contactStatuses = [
  "lead",
  "active",
  "inactive",
] as const satisfies readonly ContactStatus[];

export const contactSorts = [
  "name",
  "company",
  "status",
  "last_contacted_at",
] as const satisfies readonly ContactSort[];

/** The types a user logs by hand; `task_completed` is written by the API. */
export const loggableActivityTypes = [
  "note",
  "call",
  "email",
  "meeting",
  "follow_up",
] as const satisfies readonly ActivityType[];

export const contactSchema = (timeZone: string) =>
  z.object({
    name: requiredText("Name", 200),
    email: optionalEmail,
    phone: optionalText(50),
    job_title: optionalText(200),
    company_id: optionalId,
    status: z.enum(contactStatuses),
    last_contacted_at: optionalDateTime(timeZone),
  });

export const activitySchema = z.object({
  type: z.enum(loggableActivityTypes),
  notes: optionalNotes,
});

export type ContactInput = z.input<ReturnType<typeof contactSchema>>;
export type ActivityInput = z.input<typeof activitySchema>;

const contactSearchSchema = z.object({
  q: optionalParam(text.min(1)),
  status: optionalParam(z.enum(contactStatuses)),
  company_id: optionalParam(z.uuid()),
  ...listSearch(contactSorts),
});

export type ContactSearch = z.output<typeof contactSearchSchema>;

export function parseContactSearch(params: SearchParams | URLSearchParams): ContactSearch {
  return parseSearch(contactSearchSchema, params);
}
