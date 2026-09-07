"use client";

import type { AttachmentRead } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { ATTACHMENT_MAX_BYTES, formatBytes } from "@/lib/bytes";
import { attachmentKeys, type AttachmentParent } from "@/lib/queries";
import { contentTypeOf, putFile } from "@/lib/upload";
import { useWorkspace } from "@/lib/workspace";

export interface UploadProgress {
  id: number;
  filename: string;
  /** 0..1 while the bytes are in flight; 1 while the API confirms the upload. */
  fraction: number;
}

/**
 * Uploads run in three steps: ask the API for an upload URL, `PUT` the file
 * straight to storage, tell the API it is there. Each in-flight upload is
 * reported through `uploads` so the card can show a progress bar.
 */
export function useAttachmentMutations(parent: AttachmentParent): {
  upload: (files: FileList | File[]) => void;
  uploads: UploadProgress[];
  confirmDelete: (attachment: AttachmentRead) => void;
  dialog: ReactNode;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [uploads, setUploads] = useState<UploadProgress[]>([]);
  const [target, setTarget] = useState<AttachmentRead | null>(null);

  const queryKey = attachmentKeys.parent(workspaceId, parent);

  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const start = async (file: File) => {
    const body = { filename: file.name, content_type: contentTypeOf(file), size: file.size };
    if ("contactId" in parent) {
      return unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/contacts/{contact_id}/attachments", {
          params: { path: { workspace_id: workspaceId, contact_id: parent.contactId } },
          body,
        }),
      );
    }
    return unwrap(
      await browserApi.POST("/workspaces/{workspace_id}/companies/{company_id}/attachments", {
        params: { path: { workspace_id: workspaceId, company_id: parent.companyId } },
        body,
      }),
    );
  };

  const uploadMutation = useMutation({
    mutationFn: async ({ file, progress }: { file: File; progress: UploadProgress }) => {
      const report = (fraction: number) =>
        setUploads((list) => list.map((u) => (u.id === progress.id ? { ...u, fraction } : u)));
      const ticket = await start(file);
      await putFile(ticket.upload_url, file, ticket.attachment.content_type, report);
      report(1);
      return unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/attachments/{attachment_id}/complete", {
          params: { path: { workspace_id: workspaceId, attachment_id: ticket.attachment.id } },
        }),
      );
    },
    onSuccess: async (attachment) => {
      toast.success(`Uploaded ${attachment.filename}`);
      await invalidate();
    },
    onError: (error, { file }) => toast.error(`${file.name}: ${errorMessage(error)}`),
    onSettled: (_data, _error, { progress }) =>
      setUploads((list) => list.filter((u) => u.id !== progress.id)),
  });

  const upload = (files: FileList | File[]) => {
    for (const file of files) {
      if (file.size > ATTACHMENT_MAX_BYTES) {
        toast.error(
          `${file.name} is ${formatBytes(file.size)}; the limit is ${formatBytes(ATTACHMENT_MAX_BYTES)}.`,
        );
        continue;
      }
      const progress = { id: Date.now() + Math.random(), filename: file.name, fraction: 0 };
      setUploads((list) => [...list, progress]);
      uploadMutation.mutate({ file, progress });
    }
  };

  const deleteMutation = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE("/workspaces/{workspace_id}/attachments/{attachment_id}", {
          params: { path: { workspace_id: workspaceId, attachment_id: id } },
        }),
      ),
    onSuccess: async () => {
      toast.success("Attachment deleted");
      setTarget(null);
      await invalidate();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const dialog = (
    <ConfirmDialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open) setTarget(null);
      }}
      title={`Delete ${target?.filename ?? "attachment"}?`}
      description="The file is removed from storage. This cannot be undone."
      pending={deleteMutation.isPending}
      onConfirm={() => target && deleteMutation.mutate(target.id)}
    />
  );

  return { upload, uploads, confirmDelete: setTarget, dialog };
}
