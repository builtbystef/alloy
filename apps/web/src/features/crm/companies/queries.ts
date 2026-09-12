import type { ApiClient, CompanySort, ContactSort, SortOrder } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { contactListQuery } from "@/features/crm/contacts/queries";
import { unwrap } from "@/lib/api/errors";
import { PICKER_ROWS, paged, queryParams, type ListPage, type ListSearch } from "@/lib/lists";

export interface CompanyListFilters extends ListPage {
  q?: string | undefined;
  sort?: CompanySort | undefined;
  order?: SortOrder | undefined;
}

export const companyKeys = {
  all: ["companies"] as const,
  list: (ws: string, filters: CompanyListFilters) =>
    [...companyKeys.all, ws, "list", filters] as const,
  detail: (ws: string, id: string) => [...companyKeys.all, ws, "detail", id] as const,
};

export function companyListQuery(api: ApiClient, ws: string, filters: CompanyListFilters) {
  return queryOptions({
    queryKey: companyKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/companies/", {
          params: { path: { workspace_id: ws }, query: queryParams(filters) },
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
