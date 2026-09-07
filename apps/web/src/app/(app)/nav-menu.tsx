"use client";

import { Building2Icon, LayoutDashboardIcon, ListTodoIcon, UsersIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboardIcon },
  { href: "/contacts", label: "Contacts", icon: UsersIcon },
  { href: "/companies", label: "Companies", icon: Building2Icon },
  { href: "/tasks", label: "Tasks", icon: ListTodoIcon },
] as const;

/** The nav with the current section highlighted; needs the URL, so it streams. */
export function NavMenu() {
  return <NavLinks pathname={usePathname()} />;
}

/** The same links without a highlight: what the static shell shows. */
export function NavMenuFallback() {
  return <NavLinks pathname={null} />;
}

function NavLinks({ pathname }: { pathname: string | null }) {
  return (
    <SidebarMenu>
      {links.map(({ href, label, icon: Icon }) => {
        const active =
          pathname !== null && (href === "/" ? pathname === "/" : pathname.startsWith(href));
        return (
          <SidebarMenuItem key={href}>
            <SidebarMenuButton isActive={active} tooltip={label} render={<Link href={href} />}>
              <Icon />
              <span>{label}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      })}
    </SidebarMenu>
  );
}
