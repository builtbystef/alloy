"use client";

import { useSuspenseQuery } from "@tanstack/react-query";
import {
  BuildingIcon,
  CalendarIcon,
  CheckIcon,
  PencilIcon,
  Trash2Icon,
  UndoIcon,
  UserIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Detail } from "@/components/shared/detail-list";
import { PageHeader } from "@/components/shared/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api/client";
import { formatDateTime, formatRelativeDays, isBeforeToday } from "@/lib/formatting/dates";
import { taskQuery } from "@/features/crm/tasks/queries";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

import { TaskStatusBadge } from "./task-status-badge";
import { useTaskMutations } from "@/features/crm/tasks/hooks/use-task-mutations";

export function TaskDetail({ id, timeZone }: { id: string; timeZone: string }) {
  const router = useRouter();
  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: task } = useSuspenseQuery(taskQuery(browserApi, workspaceId, id));
  const actions = useTaskMutations({ onDeleted: () => router.push(paths.tasks) });
  const done = task.status === "done";
  const overdue = !done && isBeforeToday(task.due_at, timeZone);

  return (
    <>
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            <span className={cn(done && "text-muted-foreground line-through")}>{task.title}</span>
            <TaskStatusBadge status={task.status} />
          </span>
        }
        description={
          <span className="flex flex-wrap items-center gap-x-3">
            {task.due_at && (
              <span className={cn(overdue && "font-medium text-destructive")}>
                Due {formatRelativeDays(task.due_at, timeZone)}
              </span>
            )}
            <span>
              Added {formatDateTime(task.created_at, timeZone)}
              {task.created_by && ` by ${task.created_by.email}`}
            </span>
          </span>
        }
      >
        {canWrite && (
          <>
            <Button
              variant="outline"
              disabled={actions.pendingStatusId === task.id}
              onClick={() => actions.setStatus(task, done ? "open" : "done")}
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
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={paths.taskEdit(task.id)} />}
            >
              <PencilIcon /> Edit
            </Button>
            <Button variant="destructive" onClick={() => actions.confirmDelete(task)}>
              <Trash2Icon /> Delete
            </Button>
          </>
        )}
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-3 text-sm">
                <Detail label="Status">
                  <TaskStatusBadge status={task.status} />
                </Detail>
                <Detail icon={<CalendarIcon />} label="Due">
                  {task.due_at ? (
                    <span
                      title={formatRelativeDays(task.due_at, timeZone)}
                      className={cn(overdue && "font-medium text-destructive")}
                    >
                      {formatDateTime(task.due_at, timeZone)}
                    </span>
                  ) : null}
                </Detail>
                <Detail icon={<UserIcon />} label="Contact">
                  {task.contact ? (
                    <Link href={paths.contact(task.contact.id)} className="hover:underline">
                      {task.contact.name}
                    </Link>
                  ) : null}
                </Detail>
                <Detail icon={<BuildingIcon />} label="Company">
                  {task.company ? (
                    <Link href={paths.company(task.company.id)} className="hover:underline">
                      {task.company.name}
                    </Link>
                  ) : null}
                </Detail>
                <Detail label="Added">
                  {formatDateTime(task.created_at, timeZone)}
                  {task.created_by && (
                    <span className="text-muted-foreground"> by {task.created_by.email}</span>
                  )}
                </Detail>
                <Detail label="Updated">{formatDateTime(task.updated_at, timeZone)}</Detail>
              </dl>
            </CardContent>
          </Card>
        </div>
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              {task.notes ? (
                <p className="text-sm whitespace-pre-wrap">{task.notes}</p>
              ) : (
                <p className="text-sm text-muted-foreground">No notes.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
      {actions.dialog}
    </>
  );
}
