"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2Icon, Loader2Icon, MailIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

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

/** The link from the email: one click spends the token. */
export function ConfirmEmail({
  token,
  userEmail,
}: {
  token: string;
  /** Who is logged in on this browser, if anyone; the link itself needs no login. */
  userEmail: string | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const verify = useMutation({
    mutationFn: async () =>
      unwrap(await browserApi.POST("/auth/verify-email", { body: { token } })),
    onSuccess: (user) => {
      queryClient.clear();
      // Logged in as the account that was just verified: straight into the app.
      if (userEmail === user.email) {
        router.push("/");
        router.refresh();
      }
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 404) {
        setServerError("This link was already used or never existed.");
      } else if (error instanceof ApiError && error.status === 410) {
        setServerError("This link has expired. Log in and ask for a new one.");
      } else {
        setServerError(errorMessage(error));
      }
    },
  });

  if (verify.isSuccess) {
    const sameAccount = userEmail === verify.data.email;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2Icon className="size-5 text-primary" /> Email verified
          </CardTitle>
          <CardDescription>
            {verify.data.email} is confirmed.{" "}
            {sameAccount ? "Taking you to your workspace." : "Log in to get started."}
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
        <CardTitle>Verify your email</CardTitle>
        <CardDescription>
          Confirm that this address is yours to finish setting up your account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FormError message={serverError} />
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-3">
        <Button onClick={() => verify.mutate()} disabled={verify.isPending}>
          {verify.isPending && <Loader2Icon className="animate-spin" />}
          Verify email
        </Button>
        {serverError !== null && (
          <Button variant="ghost" nativeButton={false} render={<Link href="/verify-email" />}>
            Request a new link
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

/** The link was opened by an account that is already verified. */
export function AlreadyVerified() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle2Icon className="size-5 text-primary" /> Already verified
        </CardTitle>
        <CardDescription>
          Your email is confirmed. There is nothing left to do here.
        </CardDescription>
      </CardHeader>
      <CardFooter>
        <Button nativeButton={false} render={<Link href="/" />}>
          Go to your workspace
        </Button>
      </CardFooter>
    </Card>
  );
}

/** Just signed up: the email is on its way. */
export function CheckInbox({ email }: { email: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const resend = useMutation({
    mutationFn: async () => unwrap(await browserApi.POST("/auth/resend-verification")),
    onSuccess: () => toast.success(`A new link is on its way to ${email}.`),
    onError: (error) => {
      // 409: verified in another tab meanwhile.
      if (error instanceof ApiError && error.status === 409) {
        router.push("/");
        router.refresh();
      } else {
        toast.error(errorMessage(error));
      }
    },
  });

  const logout = useMutation({
    mutationFn: async () => unwrap(await browserApi.POST("/auth/logout")),
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
        <CardTitle className="flex items-center gap-2">
          <MailIcon className="size-5" /> Check your inbox
        </CardTitle>
        <CardDescription>
          We sent a verification link to <strong>{email}</strong>. Follow it to start using Alloy.
          The link works for one day.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          Nothing there? Check your spam folder, or ask for another email.
        </p>
      </CardContent>
      <CardFooter className="flex-col items-stretch gap-3">
        <Button variant="outline" onClick={() => resend.mutate()} disabled={resend.isPending}>
          {resend.isPending && <Loader2Icon className="animate-spin" />}
          Resend email
        </Button>
        <Button variant="ghost" onClick={() => logout.mutate()} disabled={logout.isPending}>
          Log out
        </Button>
      </CardFooter>
    </Card>
  );
}
