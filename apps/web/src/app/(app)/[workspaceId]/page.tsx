import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { Dashboard, DashboardSkeleton } from "@/features/crm/dashboard/components/dashboard";
import { getDashboard } from "@/features/crm/dashboard/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { workspacePaths } from "@/lib/routes";
import { getTimeZone } from "@/lib/time-zone/server";

export const metadata: Metadata = { title: "Dashboard" };

type Params = Promise<{ workspaceId: string }>;

export default function DashboardPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Dashboard" description="What needs your attention today." />
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent params={params} />
      </Suspense>
    </>
  );
}

async function DashboardContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const timeZone = await getTimeZone();
  const dashboard = await getDashboard(workspaceId, timeZone);
  return (
    <Dashboard dashboard={dashboard} timeZone={timeZone} paths={workspacePaths(workspaceId)} />
  );
}
