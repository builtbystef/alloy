"use client";

import type { TaskRead } from "@alloy/api-client";
import { CheckIcon, MoreHorizontalIcon, PencilIcon, Trash2Icon, UndoIcon } from "lucide-react";
import Link from "next/link";

import { createDataTableColumnHelper, SortableHeader } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { WorkspacePaths } from "@/lib/routes";
import { cn } from "@/lib/utils";

import type { useTaskMutations } from "@/features/crm/tasks/hooks/use-task-mutations";

const column = createDataTableColumnHelper<TaskRead>();

/** The list shows the names only; everything else is on the task's page. */
export function taskColumns({
  paths,
  actions,
}: {
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
    ...(actions ? [actionsColumn] : []),
  ]);
}
