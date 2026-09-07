import type {
  ActivityType,
  ContactStatus,
  DueFilter,
  TaskStatus,
  WorkspaceRole,
} from "@alloy/api-client";
import { z } from "zod";

import { wallClockToIso } from "./dates";

/**
 * Zod schemas for every form and URL the app reads. The form schemas take the
 * strings inputs produce (`z.input`) and emit the API's request bodies
 * (`z.output`): "" becomes null, which a PATCH treats as "clear this field".
 */

export const contactStatuses = [
  "lead",
  "active",
  "inactive",
] as const satisfies readonly ContactStatus[];
export const taskStatuses = ["open", "done"] as const satisfies readonly TaskStatus[];
export const workspaceRoles = [
  "owner",
  "admin",
  "member",
  "viewer",
] as const satisfies readonly WorkspaceRole[];
export const dueFilters = ["overdue", "today", "upcoming"] as const satisfies readonly DueFilter[];
/** The types a user logs by hand; `task_completed` is written by the API. */
export const loggableActivityTypes = [
  "note",
  "call",
  "email",
  "meeting",
  "follow_up",
] as const satisfies readonly ActivityType[];

const text = z.string().trim();
const emptyToNull = (value: string) => (value === "" ? null : value);

const requiredText = (label: string, max: number) =>
  text.min(1, `${label} is required`).max(max, `${label} must be at most ${max} characters`);

const optionalText = (max: number) =>
  text.max(max, `Must be at most ${max} characters`).transform(emptyToNull);

const optionalNotes = text.transform(emptyToNull);

const optionalEmail = text
  .transform(emptyToNull)
  .pipe(z.email("Enter a valid email address").nullable());

const optionalWebsite = text
  .transform(emptyToNull)
  .pipe(z.httpUrl("Enter a URL starting with http:// or https://").max(500).nullable());

/** A <select> whose empty option means "none". */
const optionalId = text.transform(emptyToNull).pipe(z.uuid("Choose an option").nullable());

/** A datetime-local value, read in the user's zone; see dates.ts. */
const optionalDateTime = (timeZone: string) =>
  text.transform(emptyToNull).pipe(
    z
      .string()
      .transform((value, ctx) => {
        const iso = wallClockToIso(value, timeZone);
        if (iso === null) ctx.addIssue({ code: "custom", message: "Enter a valid date and time" });
        return iso;
      })
      .nullable(),
  );

// Auth

const password = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(128, "Password must be at most 128 characters");

export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export const signupSchema = z
  .object({
    email: z.email("Enter a valid email address"),
    password,
    confirm: z.string(),
  })
  .refine((value) => value.password === value.confirm, {
    error: "Passwords do not match",
    path: ["confirm"],
  });

/** One input shape for the shared auth form; only sign-up checks `confirm`. */
export const authFormSchema = (mode: "login" | "signup") =>
  mode === "signup" ? signupSchema : loginSchema.extend({ confirm: z.string() });

export const passwordChangeSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: password,
    confirm: z.string(),
  })
  .refine((value) => value.new_password === value.confirm, {
    error: "Passwords do not match",
    path: ["confirm"],
  });

// Workspaces

export const workspaceSchema = z.object({
  name: requiredText("Name", 100),
});

export const inviteSchema = z.object({
  email: z.email("Enter a valid email address"),
  role: z.enum(workspaceRoles),
});

// CRM

export const companySchema = z.object({
  name: requiredText("Name", 200),
  website: optionalWebsite,
  industry: optionalText(100),
  notes: optionalNotes,
});

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

export const taskSchema = (timeZone: string) =>
  z.object({
    title: requiredText("Title", 200),
    due_at: optionalDateTime(timeZone),
    status: z.enum(taskStatuses),
    contact_id: optionalId,
    company_id: optionalId,
    notes: optionalNotes,
  });

export const activitySchema = z.object({
  type: z.enum(loggableActivityTypes),
  notes: optionalNotes,
});

export type LoginInput = z.input<typeof loginSchema>;
export type SignupInput = z.input<typeof signupSchema>;
export type AuthFormInput = z.input<ReturnType<typeof authFormSchema>>;
export type PasswordChangeInput = z.input<typeof passwordChangeSchema>;
export type WorkspaceInput = z.input<typeof workspaceSchema>;
export type InviteInput = z.input<typeof inviteSchema>;
export type CompanyInput = z.input<typeof companySchema>;
export type ContactInput = z.input<ReturnType<typeof contactSchema>>;
export type TaskInput = z.input<ReturnType<typeof taskSchema>>;
export type ActivityInput = z.input<typeof activitySchema>;

// URL search params. Anything unexpected is dropped rather than rejected,
// so a stale link still shows the list.

type SearchParams = Record<string, string | string[] | undefined>;

const optionalParam = <T extends z.ZodType>(schema: T) => schema.optional().catch(undefined);

const contactSearchSchema = z.object({
  q: optionalParam(text.min(1)),
  status: optionalParam(z.enum(contactStatuses)),
  company_id: optionalParam(z.uuid()),
});

const companySearchSchema = z.object({
  q: optionalParam(text.min(1)),
});

const taskSearchSchema = z.object({
  due: optionalParam(z.enum(dueFilters)),
  status: optionalParam(z.enum(taskStatuses)),
});

export type ContactSearch = z.output<typeof contactSearchSchema>;
export type CompanySearch = z.output<typeof companySearchSchema>;
export type TaskSearch = z.output<typeof taskSearchSchema>;

export function parseContactSearch(params: SearchParams | URLSearchParams): ContactSearch {
  return compact(contactSearchSchema.parse(toRecord(params)));
}

export function parseCompanySearch(params: SearchParams | URLSearchParams): CompanySearch {
  return compact(companySearchSchema.parse(toRecord(params)));
}

export function parseTaskSearch(params: SearchParams | URLSearchParams): TaskSearch {
  return compact(taskSearchSchema.parse(toRecord(params)));
}

/** The query string for a filter object, without empty values. */
export function toSearchString(filters: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  return params.toString();
}

function toRecord(params: SearchParams | URLSearchParams): SearchParams {
  return params instanceof URLSearchParams ? Object.fromEntries(params) : params;
}

/** Strips undefined values so equal filters produce equal query keys. */
function compact<T extends object>(value: T): T {
  return Object.fromEntries(Object.entries(value).filter(([, v]) => v !== undefined)) as T;
}
