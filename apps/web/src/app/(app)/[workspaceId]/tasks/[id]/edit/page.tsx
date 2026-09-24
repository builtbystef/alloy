import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { getSessionApi } from "@/features/auth/server";
import { taskQuery } from "@/features/crm/tasks/queries";
import { ApiError } from "@/lib/api/errors";
import { getQueryClient } from "@/lib/query-client";
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
  let task;
  try {
    task = await getQueryClient().query(taskQuery(api, workspaceId, id));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }
  return (
    <FormPage>
      <PageHeader title={task.title} />
      <TaskForm task={task} timeZone={timeZone} />
    </FormPage>
  );
}
