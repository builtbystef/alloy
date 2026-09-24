import { redirect } from "next/navigation";
import type { WorkspaceResponse } from "@alloy/api-client";
import { Suspense, type ReactNode } from "react";

import { RememberWorkspace } from "@/features/workspaces/components/remember-workspace";
import { TimeZoneSync } from "@/components/shared/time-zone-sync";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";
import { workspacePaths } from "@/lib/routes";
import { WorkspaceProvider } from "@/features/workspaces/workspace-provider";

import { AppSidebar } from "@/components/shared/layout/app-sidebar";
import { PageTitle } from "@/components/shared/layout/page-title";

type Params = Promise<{ workspaceId: string }>;

/**
 * The shell is static and prerendered. The workspace is loaded here but not
 * awaited: the promise goes to <WorkspaceProvider>, and every consumer
 * (nav links, permission gates, tables) suspends on it behind its own
 * <Suspense>, so the rest of the shell ships before the API answers.
 * <OnboardingGate> sends those who can finish an unfinished onboarding to it.
 */
export default function WorkspaceLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Params;
}) {
  const workspace = params.then(({ workspaceId }) => requireWorkspace(workspaceId));
  return (
    <WorkspaceProvider workspace={workspace}>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <Suspense>
              <PageTitle />
            </Suspense>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 p-6 md:py-8">{children}</main>
        </SidebarInset>
        <Suspense>
          <OnboardingGate workspace={workspace} />
          <CurrentTimeZone />
          <CurrentWorkspaceCookie params={params} />
        </Suspense>
      </SidebarProvider>
    </WorkspaceProvider>
  );
}

async function OnboardingGate({ workspace }: { workspace: Promise<WorkspaceResponse> }) {
  const current = await workspace;
  if (current.onboarded_at === null && current.permissions.includes("workspace:manage")) {
    redirect(workspacePaths(current.id).onboarding);
  }
  return null;
}

async function CurrentTimeZone() {
  return <TimeZoneSync serverTimeZone={await getTimeZone()} />;
}

async function CurrentWorkspaceCookie({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return <RememberWorkspace workspaceId={workspaceId} />;
}
