import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { TaskForm } from "@/features/crm/tasks/components/task-form";

export const metadata: Metadata = { title: "Edit task" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function EditTaskPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <EditTaskForm params={params} />
    </Suspense>
  );
}

async function EditTaskForm({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const { data: task } = await api.GET("/workspaces/{workspace_id}/tasks/{task_id}", {
    params: { path: { workspace_id: workspaceId, task_id: id } },
  });
  if (!task) notFound();
  return (
    <FormPage>
      <PageHeader title={task.title} />
      <TaskForm task={task} timeZone={timeZone} />
    </FormPage>
  );
}
