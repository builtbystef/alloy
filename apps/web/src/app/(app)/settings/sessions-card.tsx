"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";

export function SessionsCard() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const logoutAll = useMutation({
    mutationFn: async () => unwrap(await browserApi.POST("/auth/logout-all")),
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
          onClick={() => logoutAll.mutate()}
          disabled={logoutAll.isPending}
        >
          {logoutAll.isPending && <Loader2Icon className="animate-spin" />}
          Log out everywhere
        </Button>
      </CardContent>
    </Card>
  );
}
