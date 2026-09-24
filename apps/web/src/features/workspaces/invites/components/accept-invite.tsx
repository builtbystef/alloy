"use client";

import type { InvitePreview } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useLogout } from "@/features/auth/hooks/use-logout";
import { acceptInvite } from "@/features/workspaces/invites/mutations";
import { FormError } from "@/components/shared/form";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { errorMessage } from "@/lib/api/errors";
import { roleLabels } from "@/features/workspaces/roles";

export function AcceptInvite({
  token,
  invite,
  userEmail,
}: {
  token: string;
  invite: InvitePreview;
  /** Null when the session cookie is present but no longer valid. */
  userEmail: string | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const next = encodeURIComponent(`/invites/${token}`);
  const loginHref = `/login?next=${next}` as const;
  const signupHref = `/signup?next=${next}` as const;

  const accept = useMutation({
    mutationFn: () => acceptInvite(token),
    onSuccess: (workspace) => {
      queryClient.clear();
      router.push(`/${workspace.id}`);
      router.refresh();
    },
    onError: (error) => setServerError(errorMessage(error)),
  });

  const logout = useLogout({
    to: loginHref,
    onError: (error) => setServerError(errorMessage(error)),
  });

  const mismatch = userEmail !== null && userEmail !== invite.email;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Join {invite.workspace_name}</CardTitle>
        <CardDescription>
          {invite.invited_by ?? "Someone"} invited <strong>{invite.email}</strong> to join as{" "}
          {roleLabels[invite.role].toLowerCase()}.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <FormError message={serverError} />
        {userEmail === null && (
          <p className="text-sm text-muted-foreground">
            Create an account with {invite.email} to accept, or log in if you already have one.
          </p>
        )}
        {mismatch && (
          <p className="text-sm text-muted-foreground">
            You are logged in as <strong>{userEmail}</strong>, but this invitation is for{" "}
            <strong>{invite.email}</strong>. Log out and sign in with that address to accept it.
          </p>
        )}
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-3">
        {userEmail === null ? (
          <>
            <Button nativeButton={false} render={<Link href={signupHref} />}>
              Create an account
            </Button>
            <Button variant="outline" nativeButton={false} render={<Link href={loginHref} />}>
              Log in
            </Button>
          </>
        ) : mismatch ? (
          <Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
            {logout.isPending && <Loader2Icon className="animate-spin" />}
            Log out
          </Button>
        ) : (
          <Button onClick={() => accept.mutate()} disabled={accept.isPending}>
            {accept.isPending && <Loader2Icon className="animate-spin" />}
            Accept invitation
          </Button>
        )}
        <Button variant="ghost" nativeButton={false} render={<Link href="/" />}>
          Not now
        </Button>
      </CardFooter>
    </Card>
  );
}
