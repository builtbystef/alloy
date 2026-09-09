"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2Icon, Loader2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormError } from "@/components/form";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { ApiError, errorMessage, unwrap } from "@/lib/api-error";

export function ConfirmEmailChange({
  token,
  userId,
}: {
  token: string;
  /** Whoever is logged in on this browser, if anyone. */
  userId: string | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const confirm = useMutation({
    mutationFn: async () =>
      unwrap(await browserApi.POST("/auth/confirm-email", { body: { token } })),
    onSuccess: (user) => {
      queryClient.clear();
      if (userId === user.id) {
        router.push("/");
        router.refresh();
      }
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        setServerError("This link was already used, cancelled, or replaced by a newer one.");
      } else if (error instanceof ApiError && error.status === 410) {
        setServerError("This link has expired. Ask for a new one from your account page.");
      } else if (error instanceof ApiError && error.status === 409) {
        setServerError("This address was registered by another account in the meantime.");
      } else {
        setServerError(errorMessage(error));
      }
    },
  });

  if (confirm.isSuccess) {
    const sameAccount = userId === confirm.data.id;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2Icon className="size-5 text-primary" /> Email changed
          </CardTitle>
          <CardDescription>
            Your login is now {confirm.data.email}.{" "}
            {sameAccount ? "Taking you to your workspace." : "Log in with it to continue."}
          </CardDescription>
        </CardHeader>
        <CardFooter>
          {sameAccount ? (
            <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
          ) : (
            <Button nativeButton={false} render={<Link href="/login" />}>
              Log in
            </Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confirm your new email</CardTitle>
        <CardDescription>
          Move your account to this address. You will log in with it from now on.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FormError message={serverError} />
      </CardContent>
      <CardFooter>
        <Button className="w-full" onClick={() => confirm.mutate()} disabled={confirm.isPending}>
          {confirm.isPending && <Loader2Icon className="animate-spin" />}
          Confirm new email
        </Button>
      </CardFooter>
    </Card>
  );
}
