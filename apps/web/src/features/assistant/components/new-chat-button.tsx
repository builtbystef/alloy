"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlusIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import type { ComponentProps } from "react";
import { toast } from "sonner";

import { createConversation } from "@/features/assistant/mutations";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { conversationKeys } from "@/features/assistant/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

/** Starts a conversation and opens it. Shared by the list and the mobile bar. */
export function NewChatButton({
  children,
  ...props
}: Omit<ComponentProps<typeof Button>, "onClick" | "disabled">) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id: workspaceId, paths } = useWorkspace();

  const create = useMutation({
    mutationFn: () => createConversation(workspaceId),
    onSuccess: async (conversation) => {
      await queryClient.invalidateQueries({ queryKey: conversationKeys.list(workspaceId) });
      router.push(paths.assistantChat(conversation.id));
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Button {...props} onClick={() => create.mutate()} disabled={create.isPending}>
      <MessageSquarePlusIcon />
      {children ?? "New chat"}
    </Button>
  );
}
