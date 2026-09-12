import type { ActivityType, ContactStatus } from "@alloy/api-client";

export const contactStatusLabels: Record<ContactStatus, string> = {
  lead: "Lead",
  active: "Active",
  inactive: "Inactive",
};

export const activityTypeLabels: Record<ActivityType, string> = {
  note: "Note",
  call: "Call",
  email: "Email",
  meeting: "Meeting",
  follow_up: "Follow-up",
  task_completed: "Task completed",
};
