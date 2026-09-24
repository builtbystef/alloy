"use client";

import type { DueFilter, TaskResponse, TaskStatus } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable } from "@/components/shared/data-table";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { browserApi } from "@/lib/api/client";
import { dueFilterLabels, taskStatusLabels } from "@/features/crm/tasks/labels";
import { paged } from "@/lib/lists";
import { taskListQuery } from "@/features/crm/tasks/queries";
import {
  dueFilters,
  parseTaskSearch,
  taskStatuses,
  type TaskSearch,
} from "@/features/crm/tasks/schemas";
import { useListState } from "@/hooks/use-list-state";
import { useUrlFilters } from "@/hooks/use-url-filters";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

import { taskColumns } from "./task-columns";
import { useTaskMutations } from "@/features/crm/tasks/hooks/use-task-mutations";

export function TasksTable({
  initialFilters,
  timeZone,
}: {
  initialFilters: TaskSearch;
  timeZone: string;
}) {
  const [due, setDue] = useState<DueFilter | "">(initialFilters.due ?? "");
  const [status, setStatus] = useState<TaskStatus | "">(initialFilters.status ?? "");
  const list = useListState({
    filterKey: `${due}\0${status}`,
    initial: initialFilters,
    defaultSort: { sort: "due_at", order: "asc" },
  });
  const { deferred, isStale } = useUrlFilters(
    { due: due || undefined, status: status || undefined, ...list.search },
    parseTaskSearch,
  );

  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: tasks } = useSuspenseQuery(
    taskListQuery(browserApi, workspaceId, { ...paged(deferred), tz: timeZone }),
  );
  const actions = useTaskMutations();

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
        <span className="ml-auto text-sm text-muted-foreground">
          {tasks.total} {tasks.total === 1 ? "task" : "tasks"}
        </span>
      </div>
      <DataTable<TaskResponse>
        columns={taskColumns({ timeZone, paths, actions: canWrite ? actions : null })}
        data={tasks.items}
        total={tasks.total}
        page={list.page}
        onPageChange={list.setPage}
        sorting={list.sorting}
        onSortingChange={list.setSorting}
        emptyMessage={
          deferred.due || deferred.status
            ? "No tasks match these filters."
            : "No tasks yet. Add your first one."
        }
        className={cn(isStale && "opacity-60 transition-opacity")}
      />
      {actions.dialog}
    </div>
  );
}
