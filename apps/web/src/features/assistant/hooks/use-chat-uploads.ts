"use client";

import { useCallback, useRef } from "react";
import { toast } from "sonner";

import type {
  AddedFile,
  AttachmentControls,
  PromptAttachment,
} from "@/components/shared/chat/prompt-input";
import {
  completeChatUpload,
  discardChatUpload,
  startChatUpload,
} from "@/features/assistant/mutations";
import { errorMessage } from "@/lib/api/errors";
import { putFile } from "@/lib/api/upload";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

/**
 * Uploads files dropped into the chat while the user is still typing: ask the
 * API for an upload URL, `PUT` the bytes straight to storage, tell the API it is
 * there. Progress and the resulting upload id go back onto the attachment, so
 * the send button can wait for every file and the message can name them.
 *
 * A file removed before sending has its upload deleted again. When the removal
 * comes mid-upload, the delete waits for the upload to finish; the purge job
 * catches anything this misses.
 */
export function useChatUploads(conversationId: string): {
  onFilesAdded: (files: AddedFile[], controls: AttachmentControls) => void;
  onFileRemoved: (file: PromptAttachment) => void;
} {
  const { id: workspaceId } = useWorkspace();
  // Attachment ids removed while their upload was still running.
  const removed = useRef(new Set<string>());

  const discard = useCallback(
    (uploadId: string) => {
      void discardChatUpload(workspaceId, uploadId);
    },
    [workspaceId],
  );

  const uploadOne = useCallback(
    async ({ id, file }: AddedFile, { update }: AttachmentControls) => {
      const report = (progress: number) => update(id, { progress });
      let uploadId: string | undefined;
      try {
        const ticket = await startChatUpload(workspaceId, conversationId, file);
        uploadId = ticket.upload.id;
        if (removed.current.has(id)) return;
        await putFile(ticket.upload_url, file, ticket.upload.content_type, report);
        report(1);
        if (removed.current.has(id)) return;
        const done = await completeChatUpload(workspaceId, ticket.upload.id);
        if (removed.current.has(id)) return;
        update(id, { uploadId: done.id, progress: 1, mediaType: done.content_type });
      } catch (error) {
        if (removed.current.has(id)) return;
        const message = errorMessage(error);
        update(id, { error: message });
        toast.error(`${file.name}: ${message}`);
      } finally {
        if (removed.current.delete(id) && uploadId !== undefined) discard(uploadId);
      }
    },
    [workspaceId, conversationId, discard],
  );

  const onFileRemoved = useCallback(
    (file: PromptAttachment) => {
      if (file.uploadId !== undefined) discard(file.uploadId);
      else if (!file.error) removed.current.add(file.id);
    },
    [discard],
  );

  const onFilesAdded = useCallback(
    (files: AddedFile[], controls: AttachmentControls) => {
      for (const added of files) void uploadOne(added, controls);
    },
    [uploadOne],
  );

  return { onFilesAdded, onFileRemoved };
}
