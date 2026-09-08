"use client";

import {
  Building2Icon,
  FileUpIcon,
  LayoutDashboardIcon,
  ListTodoIcon,
  SettingsIcon,
  UsersIcon,
  UsersRoundIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";
import type { WorkspacePaths } from "@/lib/routes";
import { useWorkspace } from "@/lib/workspace";

type Section = "crm" | "workspace";
type NavKey = "home" | "contacts" | "companies" | "tasks" | "imports" | "members" | "settings";

const sections: Record<Section, readonly { key: NavKey; label: string; icon: typeof UsersIcon }[]> =
  {
    crm: [
      { key: "home", label: "Dashboard", icon: LayoutDashboardIcon },
      { key: "contacts", label: "Contacts", icon: UsersIcon },
      { key: "companies", label: "Companies", icon: Building2Icon },
      { key: "tasks", label: "Tasks", icon: ListTodoIcon },
      { key: "imports", label: "Imports", icon: FileUpIcon },
    ],
    workspace: [
      { key: "members", label: "Members", icon: UsersRoundIcon },
      { key: "settings", label: "Settings", icon: SettingsIcon },
    ],
  };

/** The nav with the current section highlighted; needs the URL and the workspace, so it streams. */
export function NavMenu({ section }: { section: Section }) {
  const { paths } = useWorkspace();
  return <NavLinks section={section} paths={paths} pathname={usePathname()} />;
}

/** The same links without a highlight or a target: what the static shell shows. */
export function NavMenuFallback({ section }: { section: Section }) {
  return <NavLinks section={section} paths={null} pathname={null} />;
}

function NavLinks({
  section,
  paths,
  pathname,
}: {
  section: Section;
  paths: WorkspacePaths | null;
  pathname: string | null;
}) {
  const home = paths?.home ?? null;
  return (
    <SidebarMenu>
      {sections[section].map(({ key, label, icon: Icon }) => {
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
