import type {
  ApiClient,
  CompanySort,
  ContactSort,
  ContactStatus,
  DueFilter,
  ImportRead,
  SortOrder,
  TaskSort,
  TaskStatus,
} from "@alloy/api-client";
import { queryOptions, type QueryClient } from "@tanstack/react-query";

import { unwrap } from "./api-error";
import type { ListSearch } from "./schemas";

/**
 * Query definitions shared by Server Components (which prefetch with the
 * session client) and Client Components (which read with the browser client).
 * The key is the identity, so both sides must build it the same way; the
 * client is a parameter rather than an import for that reason.
 *
 * Every CRM query is scoped to a workspace, so the workspace id is part of
 * the key and of the request path.
 */

/**
 * Every list the API serves is a page: `{ items, total, limit, offset }`. The
 * tables ask for a page at a time and let the total drive the pager. Feeds
 * and pickers that show everything ask for the largest page the API allows
 * and say so when there was more.
 */

/** Rows per page in the tables. */
export const PAGE_SIZE = 50;

/** The largest page the API serves, for lists that want every row. */
export const ALL_ROWS = { limit: 500, offset: 0 } as const;

/** What a picker shows per search: enough to scan, few enough to be quick. */
export const PICKER_ROWS = { limit: 20, offset: 0 } as const;

export interface ListPage {
  limit: number;
  offset: number;
}

/** The API's `limit` and `offset` for a 1-based page number. */
export function listPage(page: number | undefined, pageSize = PAGE_SIZE): ListPage {
  return { limit: pageSize, offset: ((page ?? 1) - 1) * pageSize };
}

/**
 * API list parameters for a parsed URL search: `page` becomes `limit` and
 * `offset`; `sort` and `order` pass through. Server prefetch and client
 * query must build the same key, so both go through here.
 */
export function paged<S extends string, T extends ListSearch<S>>({
  page,
  ...filters
}: T): Omit<T, "page"> & ListPage {
  return { ...filters, ...listPage(page) };
}

export interface ContactListFilters extends ListPage {
  q?: string | undefined;
  status?: ContactStatus | undefined;
  company_id?: string | undefined;
  sort?: ContactSort | undefined;
  order?: SortOrder | undefined;
}

export interface CompanyListFilters extends ListPage {
  q?: string | undefined;
  sort?: CompanySort | undefined;
  order?: SortOrder | undefined;
}

export interface TaskListFilters extends ListPage {
  due?: DueFilter | undefined;
  status?: TaskStatus | undefined;
  contact_id?: string | undefined;
  company_id?: string | undefined;
  sort?: TaskSort | undefined;
  order?: SortOrder | undefined;
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
};

export const taskKeys = {
  all: ["tasks"] as const,
  list: (ws: string, filters: TaskListFilters) => [...taskKeys.all, ws, "list", filters] as const,
};

/** Attachments hang off a contact or a company. */
export type AttachmentParent = { contactId: string } | { companyId: string };

export const attachmentKeys = {
  all: ["attachments"] as const,
  parent: (ws: string, parent: AttachmentParent) =>
    "contactId" in parent
      ? ([...attachmentKeys.all, ws, "contact", parent.contactId] as const)
      : ([...attachmentKeys.all, ws, "company", parent.companyId] as const),
};

export const importKeys = {
  all: ["imports"] as const,
  /** Every page of the list: what to invalidate after an upload. */
  lists: (ws: string) => [...importKeys.all, ws, "list"] as const,
  list: (ws: string, page: number) => [...importKeys.lists(ws), page] as const,
};

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

export function contactListQuery(api: ApiClient, ws: string, filters: ContactListFilters) {
  return queryOptions({
    queryKey: contactKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/", {
          params: { path: { workspace_id: ws }, query: query(filters) },
        }),
      ),
  });
}

/** The matches for what was typed into a contact picker, by name. */
export function contactPickerQuery(api: ApiClient, ws: string, q: string) {
  return contactListQuery(api, ws, { q: q || undefined, ...PICKER_ROWS });
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

/** The feed on a contact page: the newest 500. */
export function contactActivitiesQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: contactKeys.activities(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}/activities", {
          params: { path: { workspace_id: ws, contact_id: id }, query: ALL_ROWS },
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
          params: { path: { workspace_id: ws }, query: query(filters) },
        }),
      ),
  });
}

/** The matches for what was typed into a company picker, by name. */
export function companyPickerQuery(api: ApiClient, ws: string, q: string) {
  return companyListQuery(api, ws, { q: q || undefined, ...PICKER_ROWS });
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

/** The contacts table on a company page: the contact list, filtered to it. */
export function companyContactsQuery(
  api: ApiClient,
  ws: string,
  id: string,
  list: ListSearch<ContactSort> = {},
) {
  return contactListQuery(api, ws, { company_id: id, ...paged(list) });
}

export function taskListQuery(api: ApiClient, ws: string, filters: TaskListFilters) {
  return queryOptions({
    queryKey: taskKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/tasks/", {
          params: { path: { workspace_id: ws }, query: query(filters) },
        }),
      ),
  });
}

export function attachmentsQuery(api: ApiClient, ws: string, parent: AttachmentParent) {
  return queryOptions({
    queryKey: attachmentKeys.parent(ws, parent),
    queryFn: async () =>
      "contactId" in parent
        ? unwrap(
            await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}/attachments", {
              params: { path: { workspace_id: ws, contact_id: parent.contactId }, query: ALL_ROWS },
            }),
          )
        : unwrap(
            await api.GET("/workspaces/{workspace_id}/companies/{company_id}/attachments", {
              params: { path: { workspace_id: ws, company_id: parent.companyId }, query: ALL_ROWS },
            }),
          ),
  });
}

/** Still moving: the list polls while any import is in one of these states. */
export function isImportActive(record: ImportRead): boolean {
  return record.status === "queued" || record.status === "running";
}

const IMPORT_POLL_MS = 2000;

/** Newest first. Refetches every couple of seconds while an import is running. */
export function importListQuery(api: ApiClient, ws: string, page = 1) {
  return queryOptions({
    queryKey: importKeys.list(ws, page),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/imports/", {
          params: { path: { workspace_id: ws }, query: listPage(page) },
        }),
      ),
    refetchInterval: (query) =>
      query.state.data?.items.some(isImportActive) ? IMPORT_POLL_MS : false,
  });
}

/**
 * Where a plain link downloads an attachment. The API answers with a redirect
 * to a short-lived storage URL; through the proxy, the browser follows it as
 * a navigation, so the file saves with its own name.
 */
export function attachmentDownloadHref(ws: string, id: string): string {
  return `/api/workspaces/${ws}/attachments/${id}/download`;
}

/**
 * Drop every CRM query after a write. The entities reference each other
 * (a task embeds its contact, a completed task logs an activity, deleting a
 * company clears links, an import creates both), so anything narrower would
 * have to know those rules.
 */
export async function invalidateCrm(queryClient: QueryClient): Promise<void> {
  await Promise.all(
    [contactKeys.all, companyKeys.all, taskKeys.all, attachmentKeys.all].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}

/** Drop the workspace list, members, and invitations after a membership change. */
export async function invalidateWorkspaces(queryClient: QueryClient): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: workspaceKeys.all });
}
