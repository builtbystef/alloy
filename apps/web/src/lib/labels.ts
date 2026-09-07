import type {
  ActivityType,
  ContactStatus,
  DueFilter,
  TaskStatus,
  WorkspaceRole,
} from "@alloy/api-client";

export const contactStatusLabels: Record<ContactStatus, string> = {
  lead: "Lead",
  active: "Active",
  inactive: "Inactive",
};

export const taskStatusLabels: Record<TaskStatus, string> = {
  open: "Open",
  done: "Done",
};

export const dueFilterLabels: Record<DueFilter, string> = {
  overdue: "Overdue",
  today: "Due today",
  upcoming: "Upcoming",
};

export const activityTypeLabels: Record<ActivityType, string> = {
  note: "Note",
  call: "Call",
  email: "Email",
  meeting: "Meeting",
  follow_up: "Follow-up",
  task_completed: "Task completed",
};

export const roleLabels: Record<WorkspaceRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

export const roleDescriptions: Record<WorkspaceRole, string> = {
  owner: "Everything, including deleting the workspace.",
  admin: "Edits records, manages members and settings.",
  member: "Edits contacts, companies, and tasks.",
  viewer: "Read-only.",
};
