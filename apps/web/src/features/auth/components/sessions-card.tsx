"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { logoutAll } from "@/features/auth/mutations";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card>
      <CardHeader>
        <CardTitle>Sessions</CardTitle>
        <CardDescription>
          Sessions last 30 days. If a device is lost, log out everywhere; this one included.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          variant="destructive"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending && <Loader2Icon className="animate-spin" />}
          Log out everywhere
        </Button>
      </CardContent>
    </Card>
  );
}
