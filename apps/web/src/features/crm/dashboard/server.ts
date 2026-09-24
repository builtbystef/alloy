import "server-only";

import type { DashboardResponse } from "@alloy/api-client";

import { unwrap } from "@/lib/api/errors";
import { getSessionApi } from "@/features/auth/server";

/** The numbers and lists on the home page; `tz` decides what "today" is. */
export async function getDashboard(workspaceId: string, tz: string): Promise<DashboardResponse> {
  const api = await getSessionApi();
  return unwrap(
    await api.GET("/workspaces/{workspace_id}/dashboard/", {
      params: { path: { workspace_id: workspaceId }, query: { tz } },
    }),
  );
}
