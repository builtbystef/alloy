"use client";

import type { ConversationResponse } from "@alloy/api-client";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { deleteConversation } from "@/features/assistant/mutations";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { browserApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { formatRelativeDays } from "@/lib/formatting/dates";
import { conversationKeys, conversationListQuery } from "@/features/assistant/queries";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

import { NewChatButton } from "./new-chat-button";

/** The caller's conversations, newest first, with New chat and Delete. */
export function ConversationList({ timeZone }: { timeZone: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id: workspaceId, paths } = useWorkspace();
  const { conversationId } = useParams<{ conversationId?: string }>();
  const { data: conversations } = useSuspenseQuery(conversationListQuery(browserApi, workspaceId));
  const [target, setTarget] = useState<ConversationResponse | null>(null);

  const remove = useMutation({
    mutationFn: (id: string) => deleteConversation(workspaceId, id),
    onSuccess: async (_, id) => {
      setTarget(null);
      queryClient.removeQueries({ queryKey: conversationKeys.detail(workspaceId, id) });
      await queryClient.invalidateQueries({ queryKey: conversationKeys.list(workspaceId) });
      if (id === conversationId) router.push(paths.assistant);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="p-3">
        <NewChatButton variant="outline" className="w-full justify-start" />
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-3" aria-label="Conversations">
        {conversations.length === 0 ? (
          <p className="px-2 py-3 text-sm text-muted-foreground">No conversations yet.</p>
        ) : (
          <ul className="flex flex-col gap-px">
            {conversations.map((conversation) => {
              const active = conversation.id === conversationId;
              const title = conversation.title ?? "New conversation";
              return (
                <li key={conversation.id} className="group relative">
                  <Link
                    href={paths.assistantChat(conversation.id)}
                    className={cn(
                      "flex flex-col gap-0.5 rounded-lg px-2.5 py-2 pr-9 text-sm transition-colors hover:bg-muted",
                      active ? "bg-muted text-foreground" : "text-foreground/80",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <span className={cn("truncate", active && "font-medium")}>{title}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeDays(conversation.updated_at, timeZone)}
                    </span>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    className="absolute top-2 right-1.5 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive focus-visible:opacity-100"
                    aria-label={`Delete ${title}`}
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
        title={target ? `Delete “${target.title}”?` : "Delete this conversation?"}
        description="The transcript is removed. Files it attached to records stay on those records."
        pending={remove.isPending}
        onConfirm={() => target && remove.mutate(target.id)}
      />
    </div>
  );
}
