import type { ApiClient, DueFilter, SortOrder, TaskSort, TaskStatus } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";
import { queryParams, type ListPage } from "@/lib/lists";

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
