import type { DueFilter, TaskStatus } from "@alloy/api-client";

export const taskStatusLabels: Record<TaskStatus, string> = {
  open: "Open",
  done: "Done",
};

export const dueFilterLabels: Record<DueFilter, string> = {
  overdue: "Overdue",
  today: "Due today",
  upcoming: "Upcoming",
};
