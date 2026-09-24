import type { AttachmentResponse, AttachmentUpload } from "@alloy/api-client";

import type { AttachmentParent } from "@/features/crm/attachments/queries";
import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { contentTypeOf, putFile } from "@/lib/api/upload";

/** Step one: the row and a URL to `PUT` the bytes to. */
async function startUpload(
  ws: string,
  parent: AttachmentParent,
  file: File,
): Promise<AttachmentUpload> {
  const body = { filename: file.name, content_type: contentTypeOf(file), size: file.size };
  if ("contactId" in parent) {
    return unwrap(
      await browserApi.POST("/workspaces/{workspace_id}/contacts/{contact_id}/attachments", {
        params: { path: { workspace_id: ws, contact_id: parent.contactId } },
        body,
      }),
    );
  }
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/companies/{company_id}/attachments", {
      params: { path: { workspace_id: ws, company_id: parent.companyId } },
      body,
    }),
  );
}

/** Step three: the file is in storage; the API checks and records it. */
async function completeUpload(ws: string, attachmentId: string): Promise<AttachmentResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/attachments/{attachment_id}/complete", {
      params: { path: { workspace_id: ws, attachment_id: attachmentId } },
    }),
  );
}

/**
 * Attach a file to a contact or a company: ask the API for an upload URL,
 * `PUT` the file straight to storage, tell the API it is there. `onProgress`
 * gets 0..1 while the bytes are in flight and 1 while the API confirms.
 */
export async function uploadAttachment(
  ws: string,
  parent: AttachmentParent,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<AttachmentResponse> {
  const ticket = await startUpload(ws, parent, file);
  await putFile(ticket.upload_url, file, ticket.attachment.content_type, onProgress);
  onProgress(1);
  return completeUpload(ws, ticket.attachment.id);
}

/** The file is removed from storage too. */
export async function deleteAttachment(ws: string, id: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/attachments/{attachment_id}", {
      params: { path: { workspace_id: ws, attachment_id: id } },
    }),
  );
}
