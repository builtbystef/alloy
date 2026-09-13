"use client";

import { ChevronsUpDownIcon, LogOutIcon, SettingsIcon } from "lucide-react";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLogout } from "@/features/auth/hooks/use-logout";
import { SidebarMenuButton, useSidebar } from "@/components/ui/sidebar";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

export function UserMenu({ name, email }: { name: string; email: string }) {
  const { isMobile } = useSidebar();
  const { paths } = useWorkspace();

  const logout = useLogout();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <SidebarMenuButton
            size="lg"
            className="data-popup-open:bg-sidebar-accent data-popup-open:text-sidebar-accent-foreground"
          />
        }
      >
        <div
          aria-hidden
          className="flex aspect-square size-8 items-center justify-center rounded-lg bg-logo text-sm font-semibold text-logo-foreground uppercase"
        >
          {name.trim().charAt(0)}
        </div>
        <div className="grid flex-1 text-left text-sm leading-tight">
          <span className="truncate font-medium">{name}</span>
          <span className="truncate text-xs text-muted-foreground">{email}</span>
        </div>
        <ChevronsUpDownIcon className="ml-auto size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side={isMobile ? "bottom" : "right"}
        align="end"
        sideOffset={4}
        className="w-(--anchor-width) min-w-56"
      >
        <DropdownMenuGroup>
          <DropdownMenuLabel className="grid font-normal">
            <span className="truncate font-medium text-foreground">{name}</span>
            <span className="truncate text-xs text-muted-foreground">{email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link href={paths.account} />}>
          <SettingsIcon /> Settings
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => logout.mutate()} disabled={logout.isPending}>
          <LogOutIcon /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
