import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { Logo } from "@/components/logo";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listWorkspaces } from "@/lib/session";
import { WORKSPACE_COOKIE } from "@/lib/workspace-shared";

import { CreateWorkspaceForm } from "./workspace-form";

export const metadata: Metadata = { title: "Workspaces" };

/**
 * `/` has no content of its own: it opens the workspace the user last used
 * (cookie), else their first one. Someone with no workspace left is asked to
 * create one.
 */
export default function HomePage() {
  return (
    <Suspense>
      <OpenWorkspace />
    </Suspense>
  );
}

async function OpenWorkspace() {
  const [workspaces, cookieStore] = await Promise.all([listWorkspaces(), cookies()]);
  const remembered = cookieStore.get(WORKSPACE_COOKIE)?.value;
  const target = workspaces.find((w) => w.id === remembered) ?? workspaces[0];
  if (target) redirect(`/${target.id}`);

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-6">
        <Logo className="size-12" />
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Create a workspace</CardTitle>
            <CardDescription>
              You are not a member of any workspace. Create one to get started, or ask a colleague
              for an invitation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CreateWorkspaceForm />
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
