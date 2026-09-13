"use client";

import { SettingsIcon, UsersRoundIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "cn";

import type { WorkspacePaths } from "@/lib/routes";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

const items = [
  { key: "settings", label: "General", icon: SettingsIcon },
  { key: "members", label: "Members", icon: UsersRoundIcon },
] as const satisfies readonly {
  key: keyof WorkspacePaths;
  label: string;
  icon: typeof SettingsIcon;
}[];

/** The secondary nav of the workspace settings: a column beside the content, a row above it on phones. */
export function SettingsNav() {
  const { paths } = useWorkspace();
  return <SettingsLinks paths={paths} pathname={usePathname()} />;
}

export function SettingsNavFallback() {
  return <SettingsLinks paths={null} pathname={null} />;
}

function SettingsLinks({
  paths,
  pathname,
}: {
  paths: WorkspacePaths | null;
  pathname: string | null;
}) {
  return (
    <nav aria-label="Workspace settings" className="-mx-1 overflow-x-auto md:mx-0">
      <ul className="flex gap-1 px-1 md:flex-col md:px-0">
        {items.map(({ key, label, icon: Icon }) => {
          const href = paths?.[key] ?? null;
          // "General" is the index, so it only matches exactly; the rest own their subtree.
          const active =
            pathname !== null &&
            href !== null &&
            (key === "settings" ? pathname === href : pathname.startsWith(href));
          const className = cn(
            "flex h-8 items-center gap-2 rounded-md px-2.5 text-sm whitespace-nowrap transition-colors",
            active
              ? "bg-muted font-medium text-foreground"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          );
          return (
            <li key={key}>
              {href === null ? (
                <span className={className}>
                  <Icon className="size-4" />
                  {label}
                </span>
              ) : (
                <Link href={href} className={className} aria-current={active ? "page" : undefined}>
                  <Icon className="size-4" />
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
