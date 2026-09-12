import type { ApiClient, ImportRead } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";
import { listPage } from "@/lib/lists";

export const importKeys = {
  all: ["imports"] as const,
  /** Every page of the list: what to invalidate after an upload. */
  lists: (ws: string) => [...importKeys.all, ws, "list"] as const,
  list: (ws: string, page: number) => [...importKeys.lists(ws), page] as const,
};

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
