"use client";

import type { CompanyRead } from "@alloy/api-client";
import { ExternalLinkIcon, MoreHorizontalIcon, PencilIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";

import { createDataTableColumnHelper, SortableHeader } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate } from "@/lib/dates";
import type { WorkspacePaths } from "@/lib/routes";

const column = createDataTableColumnHelper<CompanyRead>();

/** "acme.test" for "https://acme.test/path". */
export function websiteLabel(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function companyColumns({
  timeZone,
  paths,
  onDelete,
}: {
  timeZone: string;
  paths: WorkspacePaths;
  /** Null hides the row actions (read-only roles). */
  onDelete: ((company: CompanyRead) => void) | null;
}) {
  const actionsColumn = column.display({
    id: "actions",
    cell: ({ row }) => (
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Actions for ${row.original.name}`}
              />
            }
          >
            <MoreHorizontalIcon />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem render={<Link href={paths.companyEdit(row.original.id)} />}>
              <PencilIcon /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={() => onDelete?.(row.original)}>
              <Trash2Icon /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    ),
  });

  return column.columns([
    column.accessor("name", {
      header: ({ column }) => <SortableHeader column={column}>Name</SortableHeader>,
      cell: ({ row }) => (
        <Link href={paths.company(row.original.id)} className="font-medium hover:underline">
          {row.original.name}
        </Link>
      ),
    }),
    column.accessor("industry", {
      header: ({ column }) => <SortableHeader column={column}>Industry</SortableHeader>,
      cell: ({ getValue }) => getValue() ?? <span className="text-muted-foreground">–</span>,
    }),
    column.accessor("website", {
      header: "Website",
      cell: ({ getValue }) => {
        const url = getValue();
        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 hover:underline"
          >
            {websiteLabel(url)}
            <ExternalLinkIcon className="size-3 text-muted-foreground" />
          </a>
        ) : (
          <span className="text-muted-foreground">–</span>
        );
      },
      enableSorting: false,
    }),
    column.accessor("created_at", {
      header: ({ column }) => <SortableHeader column={column}>Added</SortableHeader>,
      cell: ({ getValue }) => formatDate(getValue(), timeZone),
      sortFn: "basic",
    }),
    ...(onDelete ? [actionsColumn] : []),
  ]);
}
