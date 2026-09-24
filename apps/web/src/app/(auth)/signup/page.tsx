import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";
import { inviteFromNext } from "@/features/workspaces/invites/server";

export const metadata: Metadata = { title: "Sign up" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function SignupPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Suspense>
      <SignupContent searchParams={searchParams} />
    </Suspense>
  );
}

async function SignupContent({ searchParams }: { searchParams: SearchParams }) {
  const { next } = await searchParams;
  return <AuthForm mode="signup" invite={await inviteFromNext(next)} />;
}
