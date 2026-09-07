import type { ApiClient, ContactStatus, DueFilter, TaskStatus } from "@alloy/api-client";
import { queryOptions, type QueryClient } from "@tanstack/react-query";

import { unwrap } from "./api-error";

/**
 * Query definitions shared by Server Components (which prefetch with the
 * session client) and Client Components (which read with the browser client).
 * The key is the identity, so both sides must build it the same way; the
 * client is a parameter rather than an import for that reason.
 *
 * Every CRM query is scoped to a workspace, so the workspace id is part of
 * the key and of the request path.
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

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
  detail: (id: string) => [...workspaceKeys.all, "detail", id] as const,
  members: (id: string) => [...workspaceKeys.detail(id), "members"] as const,
  invites: (id: string) => [...workspaceKeys.detail(id), "invites"] as const,
};

export const contactKeys = {
  all: ["contacts"] as const,
  list: (ws: string, filters: ContactListFilters) =>
    [...contactKeys.all, ws, "list", filters] as const,
  detail: (ws: string, id: string) => [...contactKeys.all, ws, "detail", id] as const,
  activities: (ws: string, id: string) => [...contactKeys.detail(ws, id), "activities"] as const,
};

export const companyKeys = {
  all: ["companies"] as const,
  list: (ws: string, filters: CompanyListFilters) =>
    [...companyKeys.all, ws, "list", filters] as const,
  detail: (ws: string, id: string) => [...companyKeys.all, ws, "detail", id] as const,
  contacts: (ws: string, id: string) => [...companyKeys.detail(ws, id), "contacts"] as const,
};

export const taskKeys = {
  all: ["tasks"] as const,
  list: (ws: string, filters: TaskListFilters) => [...taskKeys.all, ws, "list", filters] as const,
};

// Workspaces

export function workspaceListQuery(api: ApiClient) {
  return queryOptions({
    queryKey: workspaceKeys.list(),
    queryFn: async () => unwrap(await api.GET("/workspaces/")),
  });
}

export function memberListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: workspaceKeys.members(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/members", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

export function inviteListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: workspaceKeys.invites(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/invites", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

// CRM

export function contactListQuery(api: ApiClient, ws: string, filters: ContactListFilters) {
  return queryOptions({
    queryKey: contactKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/", {
          params: { path: { workspace_id: ws }, query: { ...query(filters), ...PAGE } },
        }),
      ),
  });
}

export function contactQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: contactKeys.detail(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}", {
          params: { path: { workspace_id: ws, contact_id: id } },
        }),
      ),
  });
}

export function contactActivitiesQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: contactKeys.activities(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}/activities", {
          params: { path: { workspace_id: ws, contact_id: id }, query: PAGE },
        }),
      ),
  });
}

export function companyListQuery(api: ApiClient, ws: string, filters: CompanyListFilters) {
  return queryOptions({
    queryKey: companyKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/companies/", {
          params: { path: { workspace_id: ws }, query: { ...query(filters), ...PAGE } },
        }),
      ),
  });
}

export function companyQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: companyKeys.detail(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/companies/{company_id}", {
          params: { path: { workspace_id: ws, company_id: id } },
        }),
      ),
  });
}

export function companyContactsQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: companyKeys.contacts(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/companies/{company_id}/contacts", {
          params: { path: { workspace_id: ws, company_id: id } },
        }),
      ),
  });
}

export function taskListQuery(api: ApiClient, ws: string, filters: TaskListFilters) {
  return queryOptions({
    queryKey: taskKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/tasks/", {
          params: { path: { workspace_id: ws }, query: { ...query(filters), ...PAGE } },
        }),
      ),
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

/** Drop the workspace list, members, and invitations after a membership change. */
export async function invalidateWorkspaces(queryClient: QueryClient): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: workspaceKeys.all });
}
