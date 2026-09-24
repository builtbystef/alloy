import type { ChatUploadResponse, ChatUploadTicket, ConversationResponse } from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { contentTypeOf } from "@/lib/api/upload";

export async function createConversation(ws: string): Promise<ConversationResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/agent/conversations", {
      params: { path: { workspace_id: ws } },
    }),
  );
}

/** The transcript and any files sent in it go with it. */
export async function deleteConversation(ws: string, id: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/agent/conversations/{conversation_id}", {
      params: { path: { workspace_id: ws, conversation_id: id } },
    }),
  );
}

/**
 * Files sent to the assistant take the same three steps as attachments, but
 * the caller runs them, since a file can be withdrawn between any two.
 */
export async function startChatUpload(
  ws: string,
  conversationId: string,
  file: File,
): Promise<ChatUploadTicket> {
  return unwrap(
    await browserApi.POST(
      "/workspaces/{workspace_id}/agent/conversations/{conversation_id}/uploads",
      {
        params: { path: { workspace_id: ws, conversation_id: conversationId } },
        body: { filename: file.name, content_type: contentTypeOf(file), size: file.size },
      },
    ),
  );
}

export async function completeChatUpload(
  ws: string,
  uploadId: string,
): Promise<ChatUploadResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/agent/uploads/{upload_id}/complete", {
      params: { path: { workspace_id: ws, upload_id: uploadId } },
    }),
  );
}

/** Best effort: the purge job catches anything this misses. */
export async function discardChatUpload(ws: string, uploadId: string): Promise<void> {
  await browserApi.DELETE("/workspaces/{workspace_id}/agent/uploads/{upload_id}", {
    params: { path: { workspace_id: ws, upload_id: uploadId } },
  });
}
