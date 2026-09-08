import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { ResetPasswordForm } from "./reset-password-form";

export const metadata: Metadata = { title: "Reset your password" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * The link from the "forgot password" email. It needs no login, and a stale
 * cookie on this browser does not get in the way: the API replaces every
 * session with a new one when the password is set.
 */
export default function ResetPasswordPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    // The token is read at request time, so the page sits behind <Suspense>.
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <ResetPasswordContent searchParams={searchParams} />
    </Suspense>
  );
}

async function ResetPasswordContent({ searchParams }: { searchParams: SearchParams }) {
  const { token } = await searchParams;
  if (typeof token !== "string" || !token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Reset link not found</CardTitle>
          <CardDescription>
            This page needs the link from the email. Ask for a new one if yours is missing.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" nativeButton={false} render={<Link href="/forgot-password" />}>
            Request a new link
          </Button>
        </CardContent>
      </Card>
    );
  }
  return <ResetPasswordForm token={token} />;
}
