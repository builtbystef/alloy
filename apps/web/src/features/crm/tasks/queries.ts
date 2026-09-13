import type { ApiClient, DueFilter, SortOrder, TaskSort, TaskStatus } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import type { EntityOption } from "@/components/shared/entity-combobox";
import { unwrap } from "@/lib/api/errors";
import { PICKER_ROWS, queryParams, type ListPage } from "@/lib/lists";

import { splitLinkKey, type LinkKey } from "./links";

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

export const taskKeys = {
  all: ["tasks"] as const,
  list: (ws: string, filters: TaskListFilters) => [...taskKeys.all, ws, "list", filters] as const,
  detail: (ws: string, id: string) => [...taskKeys.all, ws, "detail", id] as const,
};

export function taskListQuery(api: ApiClient, ws: string, filters: TaskListFilters) {
  return queryOptions({
    queryKey: taskKeys.list(ws, filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/tasks/", {
          params: { path: { workspace_id: ws }, query: queryParams(filters) },
        }),
      ),
  });
}

export function taskQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: taskKeys.detail(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/tasks/{task_id}", {
          params: { path: { workspace_id: ws, task_id: id } },
        }),
      ),
  });
}

/** The "related to" picker's matches: contacts and companies, by name. */
export function taskLinkPickerQuery(api: ApiClient, ws: string, q: string) {
  const query = { q: q || undefined, ...PICKER_ROWS };
  return queryOptions({
    queryKey: [...taskKeys.all, ws, "links", q] as const,
    queryFn: async (): Promise<{ items: EntityOption[]; total: number }> => {
      const [contacts, companies] = await Promise.all([
        api.GET("/workspaces/{workspace_id}/contacts/", {
          params: { path: { workspace_id: ws }, query: queryParams(query) },
        }),
        api.GET("/workspaces/{workspace_id}/companies/", {
          params: { path: { workspace_id: ws }, query: queryParams(query) },
        }),
      ]);
      const people = unwrap(contacts);
      const firms = unwrap(companies);
      return {
        items: [
          ...people.items.map((c) => ({
            id: `contact:${c.id}`,
            name: c.name,
            detail: c.company ? `Contact at ${c.company.name}` : "Contact",
          })),
          ...firms.items.map((c) => ({ id: `company:${c.id}`, name: c.name, detail: "Company" })),
        ],
        total: people.total + firms.total,
      };
    },
  });
}

/** The option behind a link key, so the picker can show a name for it. */
export function taskLinkQuery(api: ApiClient, ws: string, key: string) {
  return queryOptions({
    queryKey: [...taskKeys.all, ws, "link", key] as const,
    queryFn: async (): Promise<EntityOption> => {
      const [kind, id] = splitLinkKey(key as LinkKey);
      const path = { workspace_id: ws };
      const row =
        kind === "contact"
          ? unwrap(
              await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}", {
                params: { path: { ...path, contact_id: id } },
              }),
            )
          : unwrap(
              await api.GET("/workspaces/{workspace_id}/companies/{company_id}", {
                params: { path: { ...path, company_id: id } },
              }),
            );
      return { id: key, name: row.name };
    },
  });
}
