import type { ApiClient } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";
import { ALL_ROWS } from "@/lib/lists";

/** Attachments hang off a contact or a company. */
export type AttachmentParent = { contactId: string } | { companyId: string };

export const attachmentKeys = {
  all: ["attachments"] as const,
  parent: (ws: string, parent: AttachmentParent) =>
    "contactId" in parent
      ? ([...attachmentKeys.all, ws, "contact", parent.contactId] as const)
      : ([...attachmentKeys.all, ws, "company", parent.companyId] as const),
};

export function attachmentsQuery(api: ApiClient, ws: string, parent: AttachmentParent) {
  return queryOptions({
    queryKey: attachmentKeys.parent(ws, parent),
    queryFn: async () =>
      "contactId" in parent
        ? unwrap(
            await api.GET("/workspaces/{workspace_id}/contacts/{contact_id}/attachments", {
              params: { path: { workspace_id: ws, contact_id: parent.contactId }, query: ALL_ROWS },
            }),
          )
        : unwrap(
            await api.GET("/workspaces/{workspace_id}/companies/{company_id}/attachments", {
              params: { path: { workspace_id: ws, company_id: parent.companyId }, query: ALL_ROWS },
            }),
          ),
  });
}

/**
 * Where a plain link downloads an attachment. The API answers with a redirect
 * to a short-lived storage URL; through the proxy, the browser follows it as
 * a navigation, so the file saves with its own name.
 */
export function attachmentDownloadHref(ws: string, id: string): string {
  return `/api/workspaces/${ws}/attachments/${id}/download`;
}
