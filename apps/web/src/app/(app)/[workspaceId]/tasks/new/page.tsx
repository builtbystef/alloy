import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { linkKey, type TaskLink } from "@/features/crm/tasks/links";
import { taskLinkPickerQuery, taskLinkQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { TaskForm } from "@/features/crm/tasks/components/task-form";

export const metadata: Metadata = { title: "New task" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<{ contact_id?: string | string[]; company_id?: string | string[] }>;

export default function NewTaskPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <NewTaskForm params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function NewTaskForm({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const { contact_id, company_id } = await searchParams;
  // A link from a contact or company page pre-selects that record.
  const defaults: TaskLink = {
    contact_id: typeof contact_id === "string" ? contact_id : null,
    company_id: typeof company_id === "string" ? company_id : null,
  };
  const key = linkKey(defaults);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.query(taskLinkPickerQuery(api, workspaceId, "")).catch(noop),
    key ? queryClient.query(taskLinkQuery(api, workspaceId, key)).catch(noop) : null,
  ]);
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <FormPage>
        <TaskForm timeZone={timeZone} defaults={defaults} />
      </FormPage>
    </HydrationBoundary>
  );
}
