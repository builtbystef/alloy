import type { TaskCreate, TaskRead, TaskUpdate } from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function createTask(ws: string, body: TaskCreate): Promise<TaskRead> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/tasks/", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

/** Marking a task done also logs an activity on its contact. */
export async function updateTask(ws: string, id: string, body: TaskUpdate): Promise<TaskRead> {
  return unwrap(
    await browserApi.PATCH("/workspaces/{workspace_id}/tasks/{task_id}", {
      params: { path: { workspace_id: ws, task_id: id } },
      body,
    }),
  );
}

export async function deleteTask(ws: string, id: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/tasks/{task_id}", {
      params: { path: { workspace_id: ws, task_id: id } },
    }),
  );
}
