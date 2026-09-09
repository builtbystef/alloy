"use client";

import type { CompanyRef, ContactRef } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { MoreHorizontalIcon, PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";

import { TruncatedNote } from "@/components/truncated-note";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { browserApi } from "@/lib/api-browser";
import { formatRelativeDays, isBeforeToday } from "@/lib/dates";
import { ALL_ROWS, taskListQuery } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/lib/workspace";

import { useTaskMutations } from "./use-task-mutations";

export function TaskList({
  timeZone,
  contact,
  company,
}: {
  timeZone: string;
  contact?: ContactRef;
  company?: CompanyRef;
}) {
  const filters: { contact_id?: string; company_id?: string } = contact
    ? { contact_id: contact.id }
    : company
      ? { company_id: company.id }
      : {};
  const { id: workspaceId } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: tasks } = useSuspenseQuery(
    taskListQuery(browserApi, workspaceId, { ...filters, ...ALL_ROWS, tz: timeZone }),
  );
  const actions = useTaskMutations({ timeZone, defaults: filters });
  const open = tasks.items.filter((task) => task.status === "open");
  const done = tasks.items.filter((task) => task.status === "done");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tasks</CardTitle>
        {canWrite && (
          <CardAction>
            <Button variant="outline" size="sm" onClick={actions.openCreate}>
              <PlusIcon /> Add
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        {tasks.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tasks yet.</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {[...open, ...done].map((task) => {
              const overdue = task.status === "open" && isBeforeToday(task.due_at, timeZone);
              return (
                <li key={task.id} className="group flex items-start gap-3 rounded-md py-1.5">
                  <Checkbox
                    className="mt-1"
                    checked={task.status === "done"}
                    disabled={!canWrite || actions.pendingStatusId === task.id}
                    onCheckedChange={(checked) =>
                      actions.setStatus(task, checked ? "done" : "open")
                    }
                    aria-label={`Mark "${task.title}" ${task.status === "done" ? "open" : "done"}`}
                  />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span
                      className={cn(
                        "text-sm",
                        task.status === "done" && "text-muted-foreground line-through",
                      )}
                    >
                      {task.title}
                    </span>
                    {(task.due_at || task.created_by) && (
                      <span className="text-xs text-muted-foreground">
                        {task.due_at && (
                          <span className={cn(overdue && "font-medium text-destructive")}>
                            Due {formatRelativeDays(task.due_at, timeZone)}
                          </span>
                        )}
                        {task.due_at && task.created_by && " · "}
                        {task.created_by && `Added by ${task.created_by.email}`}
                      </span>
                    )}
                  </div>
                  {canWrite && (
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 aria-expanded:opacity-100"
                            aria-label={`Actions for "${task.title}"`}
                          />
                        }
                      >
                        <MoreHorizontalIcon />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => actions.openEdit(task)}>
                          <PencilIcon /> Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={() => actions.confirmDelete(task)}
                        >
                          <Trash2Icon /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <TruncatedNote shown={tasks.items.length} total={tasks.total} noun="tasks" />
      </CardContent>
      {actions.dialogs}
    </Card>
  );
}
