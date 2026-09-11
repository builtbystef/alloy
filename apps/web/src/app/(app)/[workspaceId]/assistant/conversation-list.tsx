"use client";

import type { ConversationRead } from "@alloy/api-client";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { MessageSquarePlusIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { formatRelativeDays } from "@/lib/dates";
import { conversationKeys, conversationListQuery } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/workspace";

/** The caller's conversations, newest first, with New chat and Delete. */
export function ConversationList({ timeZone }: { timeZone: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id: workspaceId, paths } = useWorkspace();
  const { conversationId } = useParams<{ conversationId?: string }>();
  const { data: conversations } = useSuspenseQuery(conversationListQuery(browserApi, workspaceId));
  const [target, setTarget] = useState<ConversationRead | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: conversationKeys.list(workspaceId) });

  const create = useMutation({
    mutationFn: async () =>
      unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/agent/conversations", {
          params: { path: { workspace_id: workspaceId } },
        }),
      ),
    onSuccess: async (conversation) => {
      await invalidate();
      router.push(paths.assistantChat(conversation.id));
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const remove = useMutation({
    mutationFn: async (id: string) =>
      unwrap(
        await browserApi.DELETE(
          "/workspaces/{workspace_id}/agent/conversations/{conversation_id}",
          {
            params: { path: { workspace_id: workspaceId, conversation_id: id } },
          },
        ),
      ),
    onSuccess: async (_, id) => {
      setTarget(null);
      queryClient.removeQueries({ queryKey: conversationKeys.detail(workspaceId, id) });
      await invalidate();
      if (id === conversationId) router.push(paths.assistant);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <Button
        variant="outline"
        className="justify-start"
        onClick={() => create.mutate()}
        disabled={create.isPending}
      >
        <MessageSquarePlusIcon /> New chat
      </Button>
      <nav className="min-h-0 flex-1 overflow-y-auto" aria-label="Conversations">
        {conversations.length === 0 ? (
          <p className="px-2 py-3 text-sm text-muted-foreground">No conversations yet.</p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {conversations.map((conversation) => {
              const active = conversation.id === conversationId;
              return (
                <li key={conversation.id} className="group relative">
                  <Link
                    href={paths.assistantChat(conversation.id)}
                    className={cn(
                      "flex flex-col rounded-md px-2 py-1.5 pr-8 text-sm hover:bg-muted",
                      active && "bg-muted font-medium",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className="truncate">{conversation.title ?? "New conversation"}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeDays(conversation.updated_at, timeZone)}
                    </span>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    className="absolute top-1.5 right-1 text-destructive opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                    aria-label={`Delete ${conversation.title ?? "conversation"}`}
                    onClick={() => setTarget(conversation)}
                  >
                    <Trash2Icon />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
      <ConfirmDialog
        open={target !== null}
        onOpenChange={(open) => {
          if (!open) setTarget(null);
        }}
        title={`Delete ${target?.title ?? "this conversation"}?`}
        description="The transcript is removed. Files it attached to records stay on those records."
        pending={remove.isPending}
        onConfirm={() => target && remove.mutate(target.id)}
      />
    </div>
  );
}
