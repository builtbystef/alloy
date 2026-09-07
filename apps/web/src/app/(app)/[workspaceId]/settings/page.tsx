import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { requireWorkspace } from "@/lib/session";

import { DangerZone } from "./danger-zone";
import { WorkspaceNameForm } from "./workspace-name-form";

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
