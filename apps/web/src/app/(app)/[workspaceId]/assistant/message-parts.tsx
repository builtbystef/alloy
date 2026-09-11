"use client";

import { getToolName } from "ai";
import { FileIcon, FileTextIcon, ImageIcon } from "lucide-react";

import { MessageContent, MessageResponse } from "@/components/chat/message";
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from "@/components/chat/tool";
import { formatBytes } from "@/lib/bytes";

import { ApprovalCard } from "./approval-card";
import type { ApprovalPreview, ChatMessage, ChatToolPart, ChatUploadMeta } from "./chat-types";
import { toolLabel } from "./tools";

/** The files a user message was sent with, as chips above its text. */
export function UserAttachments({ uploads }: { uploads: ChatUploadMeta[] }) {
  if (uploads.length === 0) return null;
  return (
    <ul className="ml-auto flex w-fit flex-wrap justify-end gap-2" aria-label="Attached files">
      {uploads.map((upload) => (
        <li
          key={upload.id}
          className="flex h-8 items-center gap-1.5 rounded-md border border-border px-2 text-sm"
        >
          <span className="text-muted-foreground [&_svg]:size-3.5">
            {fileIcon(upload.content_type)}
          </span>
          <span className="max-w-48 truncate">{upload.filename}</span>
          <span className="text-xs text-muted-foreground">{formatBytes(upload.size)}</span>
        </li>
      ))}
    </ul>
  );
}

function fileIcon(contentType: string) {
  if (contentType.startsWith("image/")) return <ImageIcon />;
  if (contentType === "application/pdf" || contentType.startsWith("text/")) return <FileTextIcon />;
  return <FileIcon />;
}

/** The preview the API sent for a paused call: as a data part while streaming,
 * on the message's metadata after a reload. */
export function previewFor(message: ChatMessage, toolCallId: string): ApprovalPreview | undefined {
  for (const part of message.parts) {
    if (part.type === "data-approval_preview" && part.data.tool_call_id === toolCallId) {
      return part.data;
    }
  }
  return message.metadata?.approval_previews?.[toolCallId];
}

const approvalStates = new Set(["approval-requested", "approval-responded", "output-denied"]);

/**
 * One tool call: a collapsed card with its name, status, input, and output, and
 * the approval card on top when the call is waiting for, or got, a decision.
 */
export function ToolCard({
  part,
  message,
  onRespond,
}: {
  part: ChatToolPart;
  message: ChatMessage;
  onRespond: (approvalId: string, approved: boolean) => void;
}) {
  const name = getToolName(part);
  const approval = "approval" in part ? part.approval : undefined;
  return (
    <div className="flex w-full flex-col gap-2">
      {approvalStates.has(part.state) && approval && (
        <ApprovalCard
          part={part}
          preview={previewFor(message, part.toolCallId)}
          onRespond={(approved) => onRespond(approval.id, approved)}
        />
      )}
      <Tool>
        <ToolHeader type={part.type} state={part.state} title={toolLabel(name)} />
        <ToolContent>
          <ToolInput input={part.input} />
          <ToolOutput output={part.output} errorText={part.errorText} />
        </ToolContent>
      </Tool>
    </div>
  );
}

/** Every part of an assistant message, in order. */
export function AssistantParts({
  message,
  streaming,
  onRespond,
}: {
  message: ChatMessage;
  streaming: boolean;
  onRespond: (approvalId: string, approved: boolean) => void;
}) {
  return message.parts.map((part, index) => {
    switch (part.type) {
      case "text":
        return (
          <MessageContent key={index}>
            <MessageResponse mode={streaming ? "streaming" : "static"}>{part.text}</MessageResponse>
          </MessageContent>
        );
      case "dynamic-tool":
        return (
          <ToolCard key={part.toolCallId} part={part} message={message} onRespond={onRespond} />
        );
      default:
        if (part.type.startsWith("tool-")) {
          const tool = part as ChatToolPart;
          return (
            <ToolCard key={tool.toolCallId} part={tool} message={message} onRespond={onRespond} />
          );
        }
        return null;
    }
  });
}
