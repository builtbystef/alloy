import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormSkeleton } from "@/components/shared/skeletons";
import { requireWorkspace } from "@/features/workspaces/server";

import { DangerZone } from "@/features/workspaces/components/danger-zone";
import { WorkspaceNameForm } from "@/features/workspaces/components/workspace-name-form";

export const metadata: Metadata = { title: "Workspace settings" };

type Params = Promise<{ workspaceId: string }>;

export default function SettingsPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Workspace settings" />
      <Suspense fallback={<FormSkeleton />}>
        <SettingsContent params={params} />
      </Suspense>
    </>
  );
}

async function SettingsContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const workspace = await requireWorkspace(workspaceId);
  return (
    <div className="grid max-w-3xl gap-6 md:grid-cols-2">
      <WorkspaceNameForm workspace={workspace} />
      <DangerZone workspace={workspace} />
    </div>
  );
}
