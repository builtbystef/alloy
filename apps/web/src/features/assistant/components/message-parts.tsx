"use client";

import { getToolName, isToolUIPart } from "ai";
import {
  BanIcon,
  CheckIcon,
  CircleAlertIcon,
  ClockIcon,
  FileIcon,
  FileTextIcon,
  ImageIcon,
  Loader2Icon,
} from "lucide-react";
import type { ReactNode } from "react";

import { MessageContent, MessageResponse } from "@/components/shared/chat/message";
import { formatBytes } from "@/lib/formatting/bytes";
import { cn } from "@/lib/utils";

import { ApprovalCard } from "./approval-card";
import type {
  ApprovalPreview,
  ChatMessage,
  ChatToolPart,
  ChatUploadMeta,
} from "@/features/assistant/types";
import { toolLabel } from "@/features/assistant/tools";

/** The files a user message was sent with, as chips above its text. */
export function UserAttachments({ uploads }: { uploads: ChatUploadMeta[] }) {
  if (uploads.length === 0) return null;
  return (
    <ul className="ml-auto flex w-fit flex-wrap justify-end gap-2" aria-label="Attached files">
      {uploads.map((upload) => (
        <li
          key={upload.id}
          className="flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-2 text-sm"
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

type StepStatus = "running" | "waiting" | "done" | "error" | "denied";

function stepStatus(state: ChatToolPart["state"]): StepStatus {
  switch (state) {
    case "output-available":
      return "done";
    case "output-error":
      return "error";
    case "output-denied":
      return "denied";
    case "approval-requested":
      return "waiting";
    default:
      return "running";
  }
}

const stepIcons: Record<StepStatus, ReactNode> = {
  running: <Loader2Icon className="animate-spin" />,
  waiting: <ClockIcon />,
  done: <CheckIcon />,
  error: <CircleAlertIcon className="text-destructive" />,
  denied: <BanIcon />,
};

interface Step {
  key: string;
  label: string;
  status: StepStatus;
  count: number;
}

/** One row per call; a run of identical calls (same tool, same status) collapses into one. */
function toSteps(parts: ChatToolPart[]): Step[] {
  const steps: Step[] = [];
  for (const part of parts) {
    const status = stepStatus(part.state);
    const label = toolLabel(getToolName(part), { done: status === "done" });
    const last = steps.at(-1);
    if (last && last.label === label && last.status === status) last.count += 1;
    else steps.push({ key: part.toolCallId, label, status, count: 1 });
  }
  return steps;
}

/**
 * A run of tool calls, shown as a quiet list of what the assistant did, with
 * the approve / deny card above it for any call waiting on a decision.
 */
export function ToolSteps({
  parts,
  message,
  onRespond,
}: {
  parts: ChatToolPart[];
  message: ChatMessage;
  onRespond: (approvalId: string, approved: boolean) => void;
}) {
  const steps = toSteps(parts);
  return (
    <div className="my-1 flex w-full flex-col gap-3">
      {parts.map((part) => {
        const approval = "approval" in part ? part.approval : undefined;
        if (!approvalStates.has(part.state) || !approval) return null;
        return (
          <ApprovalCard
            key={part.toolCallId}
            part={part}
            preview={previewFor(message, part.toolCallId)}
            onRespond={(approved) => onRespond(approval.id, approved)}
          />
        );
      })}
      <ul className="flex flex-col gap-1.5" aria-label="Steps">
        {steps.map((step) => (
          <li
            key={step.key}
            data-status={step.status}
            className={cn(
              "flex items-center gap-2 text-sm text-muted-foreground [&_svg]:size-3.5 [&_svg]:shrink-0",
              step.status === "error" && "text-destructive",
            )}
          >
            {stepIcons[step.status]}
            <span>{step.label}</span>
            {step.count > 1 && <span className="text-xs tabular-nums">×{step.count}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Every part of an assistant message, in order. Consecutive tool calls are
 * grouped into one list so a reply reads as prose with a few quiet steps.
 */
export function AssistantParts({
  message,
  streaming,
  onRespond,
}: {
  message: ChatMessage;
  streaming: boolean;
  onRespond: (approvalId: string, approved: boolean) => void;
}) {
  const nodes: ReactNode[] = [];
  let run: ChatToolPart[] = [];
  const flush = () => {
    if (run.length === 0) return;
    const parts = run;
    run = [];
    nodes.push(
      <ToolSteps
        key={parts[0]?.toolCallId}
        parts={parts}
        message={message}
        onRespond={onRespond}
      />,
    );
  };

  message.parts.forEach((part, index) => {
    if (isToolUIPart(part)) {
      run.push(part);
      return;
    }
    flush();
    if (part.type === "text" && part.text.trim() !== "") {
      nodes.push(
        <MessageContent key={index}>
          <MessageResponse mode={streaming ? "streaming" : "static"}>{part.text}</MessageResponse>
        </MessageContent>,
      );
    }
  });
  flush();
  return nodes;
}
