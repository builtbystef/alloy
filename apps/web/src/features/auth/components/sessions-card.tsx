"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { logoutAll } from "@/features/auth/mutations";
import { Button } from "@/components/ui/button";
import { ActionRow } from "@/components/shared/layout/settings-section";
import { errorMessage } from "@/lib/api/errors";

export function SessionsCard() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: logoutAll,
    onSuccess: () => {
      queryClient.clear();
      router.push("/login");
      router.refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <ActionRow title="Log out everywhere" description="This device included.">
      <Button variant="outline" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending && <Loader2Icon className="animate-spin" />}
        Log out everywhere
      </Button>
    </ActionRow>
  );
}
