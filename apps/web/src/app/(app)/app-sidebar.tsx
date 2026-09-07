import { HexagonIcon } from "lucide-react";
import Link from "next/link";
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
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/session";

import { NavMenu, NavMenuFallback } from "./nav-menu";
import { UserMenu } from "./user-menu";

/**
 * The sidebar is a Server Component: only the nav highlight (URL) and the
 * user menu (session cookie) are dynamic, and each streams in behind its own
 * <Suspense> so the rest of the shell is prerendered.
 */
export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                <HexagonIcon className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">Alloy CRM</span>
                <span className="truncate text-xs text-muted-foreground">Tiny CRM</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <Suspense fallback={<NavMenuFallback />}>
              <NavMenu />
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

async function CurrentUserMenu() {
  const user = await requireUser();
  return <UserMenu email={user.email} />;
}
