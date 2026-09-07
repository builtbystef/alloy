import { Suspense } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { listWorkspaces, requireUser } from "@/lib/session";

import { NavMenu, NavMenuFallback } from "./nav-menu";
import { UserMenu } from "./user-menu";
import { WorkspaceSwitcher } from "./workspace-switcher";

/**
 * The sidebar is a Server Component: the workspace switcher, the nav
 * highlight, and the user menu are dynamic, and each streams in behind its
 * own <Suspense> so the rest of the shell is prerendered.
 */
export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <Suspense fallback={<Skeleton className="h-12 w-full rounded-lg" />}>
              <CurrentWorkspaceSwitcher />
            </Suspense>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>CRM</SidebarGroupLabel>
          <SidebarGroupContent>
            <Suspense fallback={<NavMenuFallback section="crm" />}>
              <NavMenu section="crm" />
            </Suspense>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <Suspense fallback={<NavMenuFallback section="workspace" />}>
              <NavMenu section="workspace" />
            </Suspense>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <Suspense fallback={<Skeleton className="h-12 w-full rounded-lg" />}>
              <CurrentUserMenu />
            </Suspense>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

async function CurrentWorkspaceSwitcher() {
  return <WorkspaceSwitcher workspaces={await listWorkspaces()} />;
}

async function CurrentUserMenu() {
  const user = await requireUser();
  return <UserMenu email={user.email} />;
}
