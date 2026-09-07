import { Suspense, type ReactNode } from "react";

import { RememberWorkspace } from "@/components/remember-workspace";
import { TimeZoneSync } from "@/components/time-zone-sync";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";
import { WorkspaceProvider } from "@/lib/workspace";

import { AppSidebar } from "./app-sidebar";

type Params = Promise<{ workspaceId: string }>;

/**
 * The shell is static and prerendered. The workspace is loaded here but not
 * awaited: the promise goes to <WorkspaceProvider>, and every consumer
 * (nav links, permission gates, tables) suspends on it behind its own
 * <Suspense>, so the rest of the shell ships before the API answers.
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
            <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
            <span className="text-sm font-medium md:hidden">Alloy CRM</span>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 p-6 md:py-8">{children}</main>
        </SidebarInset>
        <Suspense>
          <CurrentTimeZone />
          <CurrentWorkspaceCookie params={params} />
        </Suspense>
      </SidebarProvider>
    </WorkspaceProvider>
  );
}

async function CurrentTimeZone() {
  return <TimeZoneSync serverTimeZone={await getTimeZone()} />;
}

async function CurrentWorkspaceCookie({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return <RememberWorkspace workspaceId={workspaceId} />;
}
