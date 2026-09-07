"use client";

import type { DueFilter, TaskRead, TaskStatus } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { browserApi } from "@/lib/api-browser";
import { dueFilterLabels, taskStatusLabels } from "@/lib/labels";
import { taskListQuery } from "@/lib/queries";
import { dueFilters, parseTaskSearch, taskStatuses, type TaskSearch } from "@/lib/schemas";
import { useUrlFilters } from "@/lib/use-url-filters";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/lib/workspace";

import { taskColumns } from "./task-columns";
import { useTaskMutations } from "./use-task-mutations";

export function TasksTable({
  initialFilters,
  timeZone,
}: {
  initialFilters: TaskSearch;
  timeZone: string;
}) {
  const [due, setDue] = useState<DueFilter | "">(initialFilters.due ?? "");
  const [status, setStatus] = useState<TaskStatus | "">(initialFilters.status ?? "");
  const { deferred, isStale } = useUrlFilters(
    { due: due || undefined, status: status || undefined },
    parseTaskSearch,
  );

  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: tasks } = useSuspenseQuery(
    taskListQuery(browserApi, workspaceId, { ...deferred, tz: timeZone }),
  );
  const actions = useTaskMutations({ timeZone });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <NativeSelect
          value={due}
          onChange={(event) => setDue(event.target.value as DueFilter | "")}
          aria-label="Filter by due date"
        >
          <NativeSelectOption value="">Any due date</NativeSelectOption>
          {dueFilters.map((value) => (
            <NativeSelectOption key={value} value={value}>
              {dueFilterLabels[value]}
            </NativeSelectOption>
          ))}
        </NativeSelect>
        <NativeSelect
          value={status}
          onChange={(event) => setStatus(event.target.value as TaskStatus | "")}
          aria-label="Filter by status"
        >
          <NativeSelectOption value="">Open and done</NativeSelectOption>
          {taskStatuses.map((value) => (
            <NativeSelectOption key={value} value={value}>
              {taskStatusLabels[value]}
            </NativeSelectOption>
          ))}
        </NativeSelect>
        <span className="text-sm text-muted-foreground">
          {tasks.length} {tasks.length === 1 ? "task" : "tasks"}
        </span>
        {canWrite && (
          <Button className="ml-auto" onClick={actions.openCreate}>
            <PlusIcon /> New task
          </Button>
        )}
      </div>
      <DataTable<TaskRead>
        columns={taskColumns({ timeZone, paths, actions: canWrite ? actions : null })}
        data={tasks}
        emptyMessage={
          deferred.due || deferred.status
            ? "No tasks match these filters."
            : "No tasks yet. Add your first one."
        }
        className={cn(isStale && "opacity-60 transition-opacity")}
      />
      {actions.dialogs}
    </div>
  );
}
