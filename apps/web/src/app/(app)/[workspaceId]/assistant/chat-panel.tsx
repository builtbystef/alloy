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
} from "@/components/chat/conversation";
import { Loader } from "@/components/chat/loader";
import { Message, MessageAction, MessageActions, MessageContent } from "@/components/chat/message";
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
} from "@/components/chat/prompt-input";
import { Shimmer } from "@/components/chat/shimmer";
import { Suggestion, Suggestions } from "@/components/chat/suggestion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ATTACHMENT_MAX_BYTES, formatBytes } from "@/lib/bytes";
import { conversationKeys, invalidateCrm } from "@/lib/queries";
import { useCan, useWorkspace } from "@/lib/workspace";

import type { ChatMessage } from "./chat-types";
import { AssistantParts, UserAttachments } from "./message-parts";
import { changedRecords } from "./tools";
import { useChatUploads } from "./use-chat-uploads";

const SUGGESTIONS = [
  "Who have we not contacted recently?",
  "What is due today?",
  "Which companies have we not talked to this month?",
  "Add a contact",
];

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
    api: `/api/workspaces/${workspaceId}/agent/conversations/${conversationId}/messages`,
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

  const send = (text: string) => {
    void chat.sendMessage({ text });
  };

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
          <ConversationContent className="mx-auto w-full max-w-3xl">
            {messages.length === 0 && (
              <ConversationEmptyState
                icon={<SparklesIcon className="size-8" />}
                title="Ask about your workspace"
                description={
                  canWrite
                    ? "Search contacts and companies, log activities, create tasks, or attach files. Deletes and bulk changes wait for your approval."
                    : "Search contacts, companies, tasks, and activities. Your role is read-only, so the assistant will not change records."
                }
              />
            )}
            {messages.map((message, index) => (
              <Message key={message.id} from={message.role}>
                {message.role === "user" ? (
                  <>
                    <UserAttachments uploads={message.metadata?.uploads ?? []} />
                    <MessageContent>
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
                      streaming={busy && index === messages.length - 1}
                      onRespond={respond}
                    />
                    {!busy && index === messages.length - 1 && (
                      <MessageActions>
                        <MessageAction
                          tooltip="Copy"
                          onClick={() => {
                            void navigator.clipboard.writeText(textOf(message));
                            toast.success("Copied");
                          }}
                        >
                          <CopyIcon />
                        </MessageAction>
                        <MessageAction tooltip="Retry" onClick={() => void chat.regenerate()}>
                          <RefreshCwIcon />
                        </MessageAction>
                      </MessageActions>
                    )}
                  </>
                )}
              </Message>
            ))}
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

        <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 p-4 pt-2">
          {messages.length === 0 && (
            <Suggestions>
              {SUGGESTIONS.map((suggestion) => (
                <Suggestion key={suggestion} suggestion={suggestion} onClick={send} />
              ))}
            </Suggestions>
          )}
          <Composer
            busy={busy}
            status={status}
            onStop={() => void chat.stop()}
            onSend={chat.sendMessage}
          />
        </div>
      </div>
    </PromptInputProvider>
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
    <PromptInput onSubmit={submit} multiple globalDrop>
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

/** The API answers errors as `{"detail": ...}`; the transport hands the body over as the message. */
export function chatErrorMessage(error: Error): string {
  try {
    const parsed: unknown = JSON.parse(error.message);
    if (parsed && typeof parsed === "object" && "detail" in parsed) {
      const detail = (parsed as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  } catch {
    // Not JSON.
  }
  return error.message || "Something went wrong.";
}
