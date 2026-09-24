"use client";

import { useChat } from "@ai-sdk/react";
import { useQueryClient } from "@tanstack/react-query";
import { DefaultChatTransport, lastAssistantMessageIsCompleteWithApprovalResponses } from "ai";
import { CopyIcon, RefreshCwIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/shared/chat/conversation";
import { Loader } from "@/components/shared/chat/loader";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/shared/chat/message";
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputController,
  type PromptInputMessage,
} from "@/components/shared/chat/prompt-input";
import { Shimmer } from "@/components/shared/chat/shimmer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ATTACHMENT_MAX_BYTES } from "@/features/crm/attachments/limits";
import { formatBytes } from "@/lib/formatting/bytes";
import { conversationKeys } from "@/features/assistant/queries";
import { invalidateCrm } from "@/features/crm/queries";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

import type { ChatMessage } from "@/features/assistant/types";
import { AssistantParts, UserAttachments } from "./message-parts";
import { chatErrorMessage } from "@/features/assistant/errors";
import { changedRecords, toolParts } from "@/features/assistant/tools";
import { useChatUploads } from "@/features/assistant/hooks/use-chat-uploads";

/**
 * One conversation with the assistant. The browser sends only its newest
 * message; the API holds the transcript and streams the reply back through
 * the proxy. Approvals round-trip through `addToolApprovalResponse`, and a
 * finished write drops the CRM queries so the tables refresh.
 */
export function ChatPanel({
  conversationId,
  initialMessages,
  timeZone,
}: {
  conversationId: string;
  initialMessages: ChatMessage[];
  timeZone: string;
}) {
  const { id: workspaceId } = useWorkspace();
  const canWrite = useCan("crm:write");
  const queryClient = useQueryClient();
  const { onFilesAdded, onFileRemoved } = useChatUploads(conversationId);

  const transport = new DefaultChatTransport<ChatMessage>({
    api: `/api/workspaces/${workspaceId}/assistant/conversations/${conversationId}/messages`,
    prepareSendMessagesRequest: ({ id, messages, trigger, messageId }) => ({
      body: { id, trigger, messageId, messages: messages.slice(-1), tz: timeZone },
    }),
  });

  const chat = useChat<ChatMessage>({
    id: conversationId,
    messages: initialMessages,
    transport,
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithApprovalResponses,
    onFinish: ({ message }) => {
      if (changedRecords(message)) void invalidateCrm(queryClient);
      void queryClient.invalidateQueries({ queryKey: conversationKeys.list(workspaceId) });
    },
    onError: (error) => toast.error(chatErrorMessage(error)),
  });
  const { messages, status, error } = chat;
  const busy = status === "submitted" || status === "streaming";
  const last = messages.at(-1);
  const awaitingApproval =
    last?.role === "assistant" && toolParts(last).some((p) => p.state === "approval-requested");

  const respond = (approvalId: string, approved: boolean) => {
    void chat.addToolApprovalResponse({ id: approvalId, approved });
  };

  return (
    <PromptInputProvider
      onFilesAdded={onFilesAdded}
      onFileRemoved={onFileRemoved}
      maxFileSize={ATTACHMENT_MAX_BYTES}
      onError={({ file }) =>
        toast.error(
          `${file.name} is ${formatBytes(file.size)}; the limit is ${formatBytes(ATTACHMENT_MAX_BYTES)}.`,
        )
      }
    >
      <div className="flex h-full min-h-0 flex-col">
        <Conversation className="min-h-0">
          <ConversationContent className="mx-auto w-full max-w-3xl gap-6 px-4 py-6 md:px-6">
            {messages.length === 0 && <EmptyState canWrite={canWrite} />}
            {messages.map((message, index) => {
              const isLast = index === messages.length - 1;
              return (
                <Message key={message.id} from={message.role}>
                  {message.role === "user" ? (
                    <>
                      <UserAttachments uploads={message.metadata?.uploads ?? []} />
                      <MessageContent className="rounded-2xl rounded-br-md">
                        {message.parts.map((part, partIndex) =>
                          part.type === "text" ? (
                            <p key={partIndex} className="whitespace-pre-wrap">
                              {part.text}
                            </p>
                          ) : null,
                        )}
                      </MessageContent>
                    </>
                  ) : (
                    <>
                      <AssistantParts
                        message={message}
                        streaming={busy && isLast}
                        onRespond={respond}
                      />
                      {!(isLast && (busy || awaitingApproval)) && (
                        <MessageActions
                          className={cn(
                            "-ml-1.5 transition-opacity",
                            !isLast && "opacity-0 group-hover:opacity-100 focus-within:opacity-100",
                          )}
                        >
                          <MessageAction
                            tooltip="Copy"
                            onClick={() => {
                              void navigator.clipboard.writeText(textOf(message));
                              toast.success("Copied");
                            }}
                          >
                            <CopyIcon />
                          </MessageAction>
                          {isLast && (
                            <MessageAction tooltip="Retry" onClick={() => void chat.regenerate()}>
                              <RefreshCwIcon />
                            </MessageAction>
                          )}
                        </MessageActions>
                      )}
                    </>
                  )}
                </Message>
              );
            })}
            {status === "submitted" && (
              <Message from="assistant">
                <MessageContent className="flex-row items-center gap-2 text-muted-foreground">
                  <Loader />
                  <Shimmer as="span">Thinking…</Shimmer>
                </MessageContent>
              </Message>
            )}
            {error && (
              <Alert variant="destructive">
                <AlertTitle>The assistant could not answer</AlertTitle>
                <AlertDescription>{chatErrorMessage(error)}</AlertDescription>
                <div className="mt-2 flex gap-2">
                  {last?.role === "user" && (
                    <Button size="sm" variant="outline" onClick={() => void chat.regenerate()}>
                      Try again
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => chat.clearError()}>
                    Dismiss
                  </Button>
                </div>
              </Alert>
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 pb-3 md:px-6">
          <Composer
            busy={busy}
            status={status}
            onStop={() => void chat.stop()}
            onSend={chat.sendMessage}
          />
          <p className="text-center text-xs text-muted-foreground">
            {canWrite
              ? "The assistant can make mistakes. Deletes and bulk changes wait for your approval."
              : "The assistant can make mistakes. Your role is read-only, so it will not change records."}
          </p>
        </div>
      </div>
    </PromptInputProvider>
  );
}

function EmptyState({ canWrite }: { canWrite: boolean }) {
  return (
    <ConversationEmptyState className="min-h-[50vh]">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-muted text-foreground">
        <SparklesIcon className="size-6" />
      </div>
      <div className="max-w-md space-y-1.5">
        <h2 className="text-lg font-semibold tracking-tight">What can I help with?</h2>
        <p className="text-sm text-balance text-muted-foreground">
          {canWrite
            ? "Ask about your contacts, companies, and tasks, log activities, or attach files. Anything that changes records is shown to you before it happens."
            : "Ask about your contacts, companies, tasks, and activities. Your role is read-only, so nothing here changes records."}
        </p>
      </div>
    </ConversationEmptyState>
  );
}

function Composer({
  busy,
  status,
  onStop,
  onSend,
}: {
  busy: boolean;
  status: ReturnType<typeof useChat>["status"];
  onStop: () => void;
  onSend: ReturnType<typeof useChat<ChatMessage>>["sendMessage"];
}) {
  const { textInput, attachments } = usePromptInputController();
  const uploading = attachments.files.some((f) => f.uploadId === undefined && !f.error);
  const failed = attachments.files.some((f) => f.error);
  const empty = textInput.value.trim() === "" && attachments.files.length === 0;

  const submit = ({ text, files }: PromptInputMessage) => {
    const uploads = files.flatMap((file) =>
      file.uploadId
        ? [
            {
              id: file.uploadId,
              filename: file.filename ?? "file",
              content_type: file.mediaType,
              size: file.size ?? 0,
            },
          ]
        : [],
    );
    const metadata = uploads.length ? { upload_ids: uploads.map((u) => u.id), uploads } : undefined;
    void onSend(metadata ? { text: text.trim(), metadata } : { text: text.trim() });
  };

  return (
    <PromptInput
      onSubmit={submit}
      multiple
      globalDrop
      className="[&>div]:rounded-2xl [&>div]:shadow-sm"
    >
      <PromptInputAttachments>
        {(attachment) => <PromptInputAttachment data={attachment} />}
      </PromptInputAttachments>
      <PromptInputBody>
        <PromptInputTextarea placeholder="Ask the assistant, or drop a file…" disabled={false} />
      </PromptInputBody>
      <PromptInputFooter>
        <PromptInputTools>
          <PromptInputActionMenu>
            <PromptInputActionMenuTrigger aria-label="Add" />
            <PromptInputActionMenuContent>
              <PromptInputActionAddAttachments />
            </PromptInputActionMenuContent>
          </PromptInputActionMenu>
          {uploading && <span className="text-xs text-muted-foreground">Uploading…</span>}
        </PromptInputTools>
        <PromptInputSubmit
          status={status}
          className="rounded-full"
          disabled={!busy && (empty || uploading || failed)}
          onClick={
            busy
              ? (event) => {
                  event.preventDefault();
                  onStop();
                }
              : undefined
          }
        />
      </PromptInputFooter>
    </PromptInput>
  );
}

function textOf(message: ChatMessage): string {
  return message.parts.flatMap((part) => (part.type === "text" ? [part.text] : [])).join("\n\n");
}
