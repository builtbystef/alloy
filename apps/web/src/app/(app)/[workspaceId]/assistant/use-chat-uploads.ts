"use client";

import { useCallback, useRef } from "react";
import { toast } from "sonner";

import type {
  AddedFile,
  AttachmentControls,
  PromptAttachment,
} from "@/components/chat/prompt-input";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { contentTypeOf, putFile } from "@/lib/upload";
import { useWorkspace } from "@/lib/workspace";

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
      void browserApi.DELETE("/workspaces/{workspace_id}/agent/uploads/{upload_id}", {
        params: { path: { workspace_id: workspaceId, upload_id: uploadId } },
      });
    },
    [workspaceId],
  );

  const uploadOne = useCallback(
    async ({ id, file }: AddedFile, { update }: AttachmentControls) => {
      const report = (progress: number) => update(id, { progress });
      let uploadId: string | undefined;
      try {
        const ticket = unwrap(
          await browserApi.POST(
            "/workspaces/{workspace_id}/agent/conversations/{conversation_id}/uploads",
            {
              params: { path: { workspace_id: workspaceId, conversation_id: conversationId } },
              body: { filename: file.name, content_type: contentTypeOf(file), size: file.size },
            },
          ),
        );
        uploadId = ticket.upload.id;
        if (removed.current.has(id)) return;
        await putFile(ticket.upload_url, file, ticket.upload.content_type, report);
        report(1);
        if (removed.current.has(id)) return;
        const done = unwrap(
          await browserApi.POST("/workspaces/{workspace_id}/agent/uploads/{upload_id}/complete", {
            params: { path: { workspace_id: workspaceId, upload_id: ticket.upload.id } },
          }),
        );
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
