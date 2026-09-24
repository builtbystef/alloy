import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DetailSkeleton } from "@/components/shared/skeletons";
import { ApiError } from "@/lib/api/errors";
import { ALL_ROWS } from "@/lib/lists";
import { attachmentsQuery } from "@/features/crm/attachments/queries";
import { companyContactsQuery, companyQuery } from "@/features/crm/companies/queries";
import { taskListQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { CompanyDetail } from "@/features/crm/companies/components/company-detail";

export const metadata: Metadata = { title: "Company" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function CompanyPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <CompanyContent params={params} />
    </Suspense>
  );
}

async function CompanyContent({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();

  try {
    await Promise.all([
      queryClient.query(companyQuery(api, workspaceId, id)),
      queryClient.query(companyContactsQuery(api, workspaceId, id)).catch(noop),
      queryClient.query(attachmentsQuery(api, workspaceId, { companyId: id })).catch(noop),
      queryClient
        .query(taskListQuery(api, workspaceId, { company_id: id, ...ALL_ROWS, tz: timeZone }))
        .catch(noop),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CompanyDetail id={id} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
