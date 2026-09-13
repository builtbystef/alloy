import type { Metadata } from "next";
import { Suspense } from "react";

import { SettingsSection, SettingsSections } from "@/components/shared/layout/settings-section";
import { FormSkeleton } from "@/components/shared/skeletons";
import { roleLabels } from "@/features/workspaces/roles";
import { requireWorkspace } from "@/features/workspaces/server";

import { DangerZone } from "@/features/workspaces/components/danger-zone";
import { WorkspaceNameForm } from "@/features/workspaces/components/workspace-name-form";

export const metadata: Metadata = { title: "Workspace settings" };

type Params = Promise<{ workspaceId: string }>;

export default function SettingsPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <SettingsContent params={params} />
    </Suspense>
  );
}

async function SettingsContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const workspace = await requireWorkspace(workspaceId);
  const canManage = workspace.permissions.includes("workspace:manage");
  return (
    <SettingsSections>
      <SettingsSection
        title="General"
        description={
          <>
            You are {roleLabels[workspace.role].toLowerCase()} of this workspace.
            {!canManage && " Only admins and owners can rename it."}
          </>
        }
      >
        <WorkspaceNameForm workspace={workspace} />
      </SettingsSection>
      <SettingsSection title="Danger zone" description="Neither of these can be undone.">
        <DangerZone workspace={workspace} />
      </SettingsSection>
    </SettingsSections>
  );
}
