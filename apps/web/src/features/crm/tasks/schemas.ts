import type { DueFilter, TaskSort, TaskStatus } from "@alloy/api-client";
import { z } from "zod";

import { listSearch, optionalParam, parseSearch, type SearchParams } from "@/lib/lists";
import { optionalDateTime, optionalId, optionalNotes, requiredText } from "@/lib/validation";

export const taskStatuses = ["open", "done"] as const satisfies readonly TaskStatus[];
export const dueFilters = ["overdue", "today", "upcoming"] as const satisfies readonly DueFilter[];
export const taskSorts = [
  "due_at",
  "title",
  "contact",
  "company",
] as const satisfies readonly TaskSort[];

export const taskSchema = (timeZone: string) =>
  z.object({
    title: requiredText("Title", 200),
    due_at: optionalDateTime(timeZone),
    status: z.enum(taskStatuses),
    contact_id: optionalId,
    company_id: optionalId,
    notes: optionalNotes,
  });

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
