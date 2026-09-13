import type { DueFilter, TaskSort, TaskStatus } from "@alloy/api-client";
import { z } from "zod";

import { listSearch, optionalParam, parseSearch, type SearchParams } from "@/lib/lists";
import { emptyToNull, optionalDateTime, optionalNotes, requiredText, text } from "@/lib/validation";

import { linkKinds, parseLinkKey } from "./links";

export const taskStatuses = ["open", "done"] as const satisfies readonly TaskStatus[];
export const dueFilters = ["overdue", "today", "upcoming"] as const satisfies readonly DueFilter[];
export const taskSorts = [
  "due_at",
  "title",
  "contact",
  "company",
] as const satisfies readonly TaskSort[];

/** The "related to" picker's value; see links.ts. */
const optionalLink = text
  .transform(emptyToNull)
  .pipe(
    z.templateLiteral([z.enum(linkKinds), ":", z.uuid()], { error: "Choose an option" }).nullable(),
  );

export const taskSchema = (timeZone: string) =>
  z
    .object({
      title: requiredText("Title", 200),
      due_at: optionalDateTime(timeZone),
      status: z.enum(taskStatuses),
      related: optionalLink,
      notes: optionalNotes,
    })
    .transform(({ related, ...task }) => ({ ...task, ...parseLinkKey(related) }));

export type TaskInput = z.input<ReturnType<typeof taskSchema>>;

const taskSearchSchema = z.object({
  due: optionalParam(z.enum(dueFilters)),
  status: optionalParam(z.enum(taskStatuses)),
  ...listSearch(taskSorts),
});

export type TaskSearch = z.output<typeof taskSearchSchema>;

export function parseTaskSearch(params: SearchParams | URLSearchParams): TaskSearch {
  return parseSearch(taskSearchSchema, params);
}
