"use client";

import type { ContactRead } from "@alloy/api-client";
import { MoreHorizontalIcon, PencilIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";

import { createDataTableColumnHelper, SortableHeader } from "@/components/data-table";
import { ContactStatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatRelativeDays } from "@/lib/dates";
import type { WorkspacePaths } from "@/lib/routes";

const column = createDataTableColumnHelper<ContactRead>();

export function contactColumns({
  timeZone,
  paths,
  onDelete,
  showCompany = true,
}: {
  timeZone: string;
  paths: WorkspacePaths;
  /** Null hides the row actions (read-only roles). */
  onDelete: ((contact: ContactRead) => void) | null;
  showCompany?: boolean;
}) {
  const companyColumn = column.accessor((row) => row.company?.name ?? "", {
    id: "company",
    header: ({ column }) => <SortableHeader column={column}>Company</SortableHeader>,
    cell: ({ row }) =>
      row.original.company ? (
        <Link href={paths.company(row.original.company.id)} className="hover:underline">
          {row.original.company.name}
        </Link>
      ) : (
        <span className="text-muted-foreground">–</span>
      ),
  });

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
            <DropdownMenuItem render={<Link href={paths.contactEdit(row.original.id)} />}>
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
        <div className="flex flex-col">
          <Link href={paths.contact(row.original.id)} className="font-medium hover:underline">
            {row.original.name}
          </Link>
          {row.original.job_title && (
            <span className="text-xs text-muted-foreground">{row.original.job_title}</span>
          )}
        </div>
      ),
    }),
    column.accessor("email", {
      header: "Email",
      cell: ({ getValue }) => {
        const email = getValue();
        return email ? (
          <a href={`mailto:${email}`} className="hover:underline">
            {email}
          </a>
        ) : (
          <span className="text-muted-foreground">–</span>
        );
      },
      enableSorting: false,
    }),
    ...(showCompany ? [companyColumn] : []),
    column.accessor("status", {
      header: ({ column }) => <SortableHeader column={column}>Status</SortableHeader>,
      cell: ({ getValue }) => <ContactStatusBadge status={getValue()} />,
    }),
    column.accessor((row) => row.last_contacted_at ?? undefined, {
      id: "last_contacted_at",
      header: ({ column }) => <SortableHeader column={column}>Last contacted</SortableHeader>,
      cell: ({ getValue }) => {
        const value = getValue();
        return value ? (
          <span title={value}>{formatRelativeDays(value, timeZone)}</span>
        ) : (
          <span className="text-muted-foreground">Never</span>
        );
      },
      sortFn: "basic",
      sortUndefined: "last",
    }),
    ...(onDelete ? [actionsColumn] : []),
  ]);
}
