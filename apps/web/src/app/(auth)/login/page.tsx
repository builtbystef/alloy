import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";
import { inviteFromNext } from "@/features/workspaces/invites/server";

export const metadata: Metadata = { title: "Log in" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Suspense>
      <LoginContent searchParams={searchParams} />
    </Suspense>
  );
}

async function LoginContent({ searchParams }: { searchParams: SearchParams }) {
  const { next } = await searchParams;
  return <AuthForm mode="login" invite={await inviteFromNext(next)} />;
}
