import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { getCurrentUser } from "@/lib/session";

import { ConfirmEmailChange } from "./confirm-email-card";

export const metadata: Metadata = { title: "Confirm your new email" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * Needs no login, and is spent by a click rather than by loading, so a mail
 * scanner that prefetches the link does not use it up.
 */
export default function ConfirmEmailPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Suspense fallback={<Skeleton className="h-56 w-full" />}>
      <ConfirmEmailContent searchParams={searchParams} />
    </Suspense>
  );
}

async function ConfirmEmailContent({ searchParams }: { searchParams: SearchParams }) {
  const [{ token }, user] = await Promise.all([searchParams, getCurrentUser()]);
  if (typeof token !== "string" || !token) redirect("/");
  return <ConfirmEmailChange token={token} userId={user?.id ?? null} />;
}
