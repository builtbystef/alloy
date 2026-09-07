"use client";

import type { WorkspaceRead } from "@alloy/api-client";
import { CheckIcon, ChevronsUpDownIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenuButton, useSidebar } from "@/components/ui/sidebar";
import { roleLabels } from "@/lib/labels";
import { useWorkspace } from "@/lib/workspace";

import { WorkspaceDialog } from "../workspace-form";

export function WorkspaceSwitcher({ workspaces }: { workspaces: WorkspaceRead[] }) {
  const current = useWorkspace();
  const { isMobile } = useSidebar();
  const [creating, setCreating] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <SidebarMenuButton
              size="lg"
              className="data-popup-open:bg-sidebar-accent data-popup-open:text-sidebar-accent-foreground"
            />
          }
        >
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary/10">
            <Logo className="size-5" />
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-semibold">{current.name}</span>
            <span className="truncate text-xs text-muted-foreground">
              {roleLabels[current.role]}
            </span>
          </div>
          <ChevronsUpDownIcon className="ml-auto size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side={isMobile ? "bottom" : "right"}
          align="start"
          sideOffset={4}
          className="w-(--anchor-width) min-w-56"
        >
          <DropdownMenuGroup>
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Workspaces
            </DropdownMenuLabel>
            {workspaces.map((workspace) => (
              <DropdownMenuItem
                key={workspace.id}
                render={<Link href={`/${workspace.id}`} />}
                className="gap-2"
              >
                <span className="truncate">{workspace.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {roleLabels[workspace.role]}
                </span>
                {workspace.id === current.id && <CheckIcon className="size-4" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreating(true)}>
            <PlusIcon /> New workspace
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <WorkspaceDialog open={creating} onOpenChange={setCreating} />
    </>
  );
}
