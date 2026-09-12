import type { ImportKind, ImportStatus } from "@alloy/api-client";

export const importKindLabels: Record<ImportKind, string> = {
  contacts: "Contacts",
  companies: "Companies",
};

export const importStatusLabels: Record<ImportStatus, string> = {
  pending: "Waiting for file",
  queued: "Queued",
  running: "Running",
  done: "Done",
  failed: "Failed",
};
