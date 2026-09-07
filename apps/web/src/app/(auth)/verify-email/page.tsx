import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { getCurrentUser } from "@/lib/session";

import { AlreadyVerified, CheckInbox, ConfirmEmail } from "./verify-email-cards";

export const metadata: Metadata = { title: "Verify your email" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * Two visitors land here. One followed the link in the email, with a token
 * in the URL, and may not be logged in: they confirm with a click, so a mail
 * scanner that prefetches the link does not spend it. The other just signed
 * up and is waiting for that email; they can ask for another.
 */
export default function VerifyEmailPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Suspense fallback={<Skeleton className="h-56 w-full" />}>
      <VerifyEmailContent searchParams={searchParams} />
    </Suspense>
  );
}

async function VerifyEmailContent({ searchParams }: { searchParams: SearchParams }) {
  const [{ token }, user] = await Promise.all([searchParams, getCurrentUser()]);
  if (typeof token === "string" && token) {
    // A spent link, most often after accepting an invitation verified the address.
    if (user !== null && user.email_verified_at !== null) return <AlreadyVerified />;
    return <ConfirmEmail token={token} userEmail={user?.email ?? null} />;
  }
  if (user === null) redirect("/login");
  if (user.email_verified_at !== null) redirect("/");
  return <CheckInbox email={user.email} />;
}
