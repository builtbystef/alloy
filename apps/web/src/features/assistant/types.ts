import type { DynamicToolUIPart, ToolUIPart, UIMessage, UIMessagePart } from "ai";

/** A file the user sent with a message, as the API records it on the transcript. */
export interface ChatUploadMeta {
  id: string;
  filename: string;
  content_type: string;
  size: number;
}

/** What a paused tool call is about to do; sent by the API for the approval card. */
export interface ApprovalPreview {
  tool_call_id: string | null;
  title: string;
  columns: string[];
  rows: string[][];
  total: number;
}

/**
 * `UIMessage.metadata` as this app uses it. A user message carries the files it
 * sent (`upload_ids` for the API, `uploads` for display); an assistant message
 * that paused for approval carries the previews, so a reload can show them.
 */
export interface ChatMetadata {
  upload_ids?: string[];
  uploads?: ChatUploadMeta[];
  approval_previews?: Record<string, ApprovalPreview>;
}

// A type alias, not an interface: `UIDataTypes` wants an implicit index signature.
export type ChatData = {
  approval_preview: ApprovalPreview;
};

export type ChatMessage = UIMessage<ChatMetadata, ChatData>;
export type ChatPart = UIMessagePart<ChatData, Record<string, never>>;
export type ChatToolPart = ToolUIPart | DynamicToolUIPart;
