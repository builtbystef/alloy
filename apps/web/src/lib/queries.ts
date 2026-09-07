import type { ApiClient, ContactStatus, DueFilter, TaskStatus } from "@alloy/api-client";
import { queryOptions, type QueryClient } from "@tanstack/react-query";

import { unwrap } from "./api-error";

/**
 * Query definitions shared by Server Components (which prefetch with the
 * session client) and Client Components (which read with the browser client).
 * The key is the identity, so both sides must build it the same way; the
 * client is a parameter rather than an import for that reason.
 */

// The API's maximum page. Enough for the demo; a real list would paginate.
const PAGE = { limit: 500 } as const;

export interface ContactListFilters {
  q?: string | undefined;
  status?: ContactStatus | undefined;
  company_id?: string | undefined;
}

export interface CompanyListFilters {
  q?: string | undefined;
}

export interface TaskListFilters {
  due?: DueFilter | undefined;
  status?: TaskStatus | undefined;
  contact_id?: string | undefined;
  company_id?: string | undefined;
  /** IANA zone that defines "today" for `due`. */
  tz: string;
}

/** Drops undefined entries, which openapi-fetch would otherwise serialize. */
function query<T extends object>(filters: T): { [K in keyof T]?: Exclude<T[K], undefined> } {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== undefined)) as {
    [K in keyof T]?: Exclude<T[K], undefined>;
  };
}

export const contactKeys = {
  all: ["contacts"] as const,
  list: (filters: ContactListFilters) => [...contactKeys.all, "list", filters] as const,
  detail: (id: string) => [...contactKeys.all, "detail", id] as const,
  activities: (id: string) => [...contactKeys.detail(id), "activities"] as const,
};

export const companyKeys = {
  all: ["companies"] as const,
  list: (filters: CompanyListFilters) => [...companyKeys.all, "list", filters] as const,
  detail: (id: string) => [...companyKeys.all, "detail", id] as const,
  contacts: (id: string) => [...companyKeys.detail(id), "contacts"] as const,
};

export const taskKeys = {
  all: ["tasks"] as const,
  list: (filters: TaskListFilters) => [...taskKeys.all, "list", filters] as const,
};

export function contactListQuery(api: ApiClient, filters: ContactListFilters) {
  return queryOptions({
    queryKey: contactKeys.list(filters),
    queryFn: async () =>
      unwrap(await api.GET("/contacts/", { params: { query: { ...query(filters), ...PAGE } } })),
  });
}

export function contactQuery(api: ApiClient, id: string) {
  return queryOptions({
    queryKey: contactKeys.detail(id),
    queryFn: async () =>
      unwrap(await api.GET("/contacts/{contact_id}", { params: { path: { contact_id: id } } })),
  });
}

export function contactActivitiesQuery(api: ApiClient, id: string) {
  return queryOptions({
    queryKey: contactKeys.activities(id),
    queryFn: async () =>
      unwrap(
        await api.GET("/contacts/{contact_id}/activities", {
          params: { path: { contact_id: id }, query: PAGE },
        }),
      ),
  });
}

export function companyListQuery(api: ApiClient, filters: CompanyListFilters) {
  return queryOptions({
    queryKey: companyKeys.list(filters),
    queryFn: async () =>
      unwrap(await api.GET("/companies/", { params: { query: { ...query(filters), ...PAGE } } })),
  });
}

export function companyQuery(api: ApiClient, id: string) {
  return queryOptions({
    queryKey: companyKeys.detail(id),
    queryFn: async () =>
      unwrap(await api.GET("/companies/{company_id}", { params: { path: { company_id: id } } })),
  });
}

export function companyContactsQuery(api: ApiClient, id: string) {
  return queryOptions({
    queryKey: companyKeys.contacts(id),
    queryFn: async () =>
      unwrap(
        await api.GET("/companies/{company_id}/contacts", {
          params: { path: { company_id: id } },
        }),
      ),
  });
}

export function taskListQuery(api: ApiClient, filters: TaskListFilters) {
  return queryOptions({
    queryKey: taskKeys.list(filters),
    queryFn: async () =>
      unwrap(await api.GET("/tasks/", { params: { query: { ...query(filters), ...PAGE } } })),
  });
}

/**
 * Drop every CRM query after a write. The entities reference each other
 * (a task embeds its contact, a completed task logs an activity, deleting a
 * company clears links), so anything narrower would have to know those rules.
 */
export async function invalidateCrm(queryClient: QueryClient): Promise<void> {
  await Promise.all(
    [contactKeys.all, companyKeys.all, taskKeys.all].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}
