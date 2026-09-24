"use client";

import {
  Building2Icon,
  LayoutDashboardIcon,
  ListTodoIcon,
  SparklesIcon,
  UsersIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import type { WorkspacePaths } from "@/lib/routes";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

type NavKey = "home" | "contacts" | "companies" | "tasks" | "assistant";

/** Workspace settings and the account live in the switcher and user menus, not here. */
const items: readonly { key: NavKey; label: string; icon: typeof UsersIcon }[] = [
  { key: "home", label: "Dashboard", icon: LayoutDashboardIcon },
  { key: "contacts", label: "Contacts", icon: UsersIcon },
  { key: "companies", label: "Companies", icon: Building2Icon },
  { key: "tasks", label: "Tasks", icon: ListTodoIcon },
  { key: "assistant", label: "Assistant", icon: SparklesIcon },
];

/** The nav with the current section highlighted; needs the URL and the workspace, so it streams. */
export function NavMenu() {
  const { paths } = useWorkspace();
  return <NavLinks paths={paths} pathname={usePathname()} />;
}

/** The same links without a highlight or a target: what the static shell shows. */
export function NavMenuFallback() {
  return <NavLinks paths={null} pathname={null} />;
}

function NavLinks({ paths, pathname }: { paths: WorkspacePaths | null; pathname: string | null }) {
  const home = paths?.home ?? null;
  return (
    <SidebarMenu>
      {items.map(({ key, label, icon: Icon }) => {
        const href = paths?.[key] ?? null;
        const active =
          pathname !== null &&
          href !== null &&
          (href === home ? pathname === home : pathname.startsWith(href));
        return (
          <SidebarMenuItem key={key}>
            <SidebarMenuButton
              isActive={active}
              tooltip={label}
              render={href === null ? <span /> : <Link href={href} />}
            >
              <Icon />
              <span>{label}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      })}
    </SidebarMenu>
  );
}
