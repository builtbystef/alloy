import type { ApiClient, ContactSort, ContactStatus, SortOrder } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";
import { ALL_ROWS, PICKER_ROWS, queryParams, type ListPage } from "@/lib/lists";

/**
 * Shared by server prefetches and client reads, which must build the same
 * key: that is why the client is a parameter rather than an import.
 */

export interface ContactListFilters extends ListPage {
  q?: string | undefined;
  status?: ContactStatus | undefined;
  company_id?: string | undefined;
  sort?: ContactSort | undefined;
  order?: SortOrder | undefined;
}

export const contactKeys = {
  all: ["contacts"] as const,
  list: (ws: string, filters: ContactListFilters) =>
    [...contactKeys.all, ws, "list", filters] as const,
  detail: (ws: string, id: string) => [...contactKeys.all, ws, "detail", id] as const,
  activities: (ws: string, id: string) => [...contactKeys.detail(ws, id), "activities"] as const,
};

export function contactListQuery(api: ApiClient, ws: string, filters: ContactListFilters) {
  return queryOptions({
    queryKey: contactKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/contacts/", {
          params: { path: { workspace_id: ws }, query: queryParams(filters) },
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
