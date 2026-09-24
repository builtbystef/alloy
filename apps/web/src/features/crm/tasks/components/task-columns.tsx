"use client";

import type { TaskResponse } from "@alloy/api-client";
import { CheckIcon, MoreHorizontalIcon, PencilIcon, Trash2Icon, UndoIcon } from "lucide-react";
import Link from "next/link";

import { createDataTableColumnHelper, SortableHeader } from "@/components/shared/data-table";
import { TaskStatusBadge } from "@/features/crm/tasks/components/task-status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDateTime, formatRelativeDays, isBeforeToday } from "@/lib/formatting/dates";
import type { WorkspacePaths } from "@/lib/routes";
import { cn } from "@/lib/utils";

import type { useTaskMutations } from "@/features/crm/tasks/hooks/use-task-mutations";

const column = createDataTableColumnHelper<TaskResponse>();

/** Title, due date, status, and what the task is about; notes are on the task's page. */
export function taskColumns({
  timeZone,
  paths,
  actions,
}: {
  timeZone: string;
  paths: WorkspacePaths;
  /** Null hides the row actions (read-only roles). */
  actions: ReturnType<typeof useTaskMutations> | null;
}) {
  const actionsColumn = column.display({
    id: "actions",
    cell: ({ row }) => {
      const task = row.original;
      const done = task.status === "done";
      return (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button variant="ghost" size="icon-sm" aria-label={`Actions for "${task.title}"`} />
              }
            >
              <MoreHorizontalIcon />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                disabled={actions?.pendingStatusId === task.id}
                onClick={() => actions?.setStatus(task, done ? "open" : "done")}
              >
                {done ? (
                  <>
                    <UndoIcon /> Reopen
                  </>
                ) : (
                  <>
                    <CheckIcon /> Mark done
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuItem render={<Link href={paths.taskEdit(task.id)} />}>
                <PencilIcon /> Edit
              </DropdownMenuItem>
              <DropdownMenuItem variant="destructive" onClick={() => actions?.confirmDelete(task)}>
                <Trash2Icon /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  });

  return column.columns([
    column.accessor("title", {
      header: ({ column }) => <SortableHeader column={column}>Task</SortableHeader>,
      cell: ({ row }) => (
        <Link
          href={paths.task(row.original.id)}
          className={cn(
            "font-medium hover:underline",
            row.original.status === "done" && "text-muted-foreground line-through",
          )}
        >
          {row.original.title}
        </Link>
      ),
    }),
    column.accessor("due_at", {
      header: ({ column }) => <SortableHeader column={column}>Due</SortableHeader>,
      cell: ({ row }) => {
        const task = row.original;
        if (!task.due_at) return <span className="text-muted-foreground">–</span>;
        const overdue = task.status === "open" && isBeforeToday(task.due_at, timeZone);
        return (
          <span
            title={formatDateTime(task.due_at, timeZone)}
            className={cn(overdue && "font-medium text-destructive")}
          >
            {formatRelativeDays(task.due_at, timeZone)}
          </span>
        );
      },
    }),
    column.accessor("status", {
      header: "Status",
      cell: ({ row }) => <TaskStatusBadge status={row.original.status} />,
    }),
    column.accessor((row) => row.contact?.name ?? "", {
      id: "contact",
      header: ({ column }) => <SortableHeader column={column}>Contact</SortableHeader>,
      cell: ({ row }) =>
        row.original.contact ? (
          <Link href={paths.contact(row.original.contact.id)} className="hover:underline">
            {row.original.contact.name}
          </Link>
        ) : (
          <span className="text-muted-foreground">–</span>
        ),
    }),
    column.accessor((row) => row.company?.name ?? "", {
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
    }),
    ...(actions ? [actionsColumn] : []),
  ]);
}
