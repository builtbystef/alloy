"use client";

import type { AttachmentRead } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import { deleteAttachment, uploadAttachment } from "@/features/crm/attachments/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { errorMessage } from "@/lib/api/errors";
import { ATTACHMENT_MAX_BYTES } from "@/features/crm/attachments/limits";
import { formatBytes } from "@/lib/formatting/bytes";
import { attachmentKeys, type AttachmentParent } from "@/features/crm/attachments/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

export interface UploadProgress {
  id: number;
  filename: string;
  /** 0..1 while the bytes are in flight; 1 while the API confirms the upload. */
  fraction: number;
}

/**
 * Each in-flight upload is reported through `uploads` so the card can show a
 * progress bar; files over the limit are refused before anything is sent.
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

  const uploadMutation = useMutation({
    mutationFn: ({ file, progress }: { file: File; progress: UploadProgress }) =>
      uploadAttachment(workspaceId, parent, file, (fraction) =>
        setUploads((list) => list.map((u) => (u.id === progress.id ? { ...u, fraction } : u))),
      ),
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
    mutationFn: (id: string) => deleteAttachment(workspaceId, id),
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
