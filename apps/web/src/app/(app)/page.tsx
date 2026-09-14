import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { listPendingInvites, listWorkspaces } from "@/features/workspaces/server";
import { WORKSPACE_COOKIE } from "@/features/workspaces/cookie";

export const metadata: Metadata = { title: "Workspaces" };

/**
 * `/` has no content of its own: it opens the workspace the user last used
 * (cookie), else their first one. With none: pending invitations, else onboarding.
 */
export default function HomePage() {
  return (
    <Suspense>
      <OpenWorkspace />
    </Suspense>
  );
}

async function OpenWorkspace(): Promise<never> {
  const [workspaces, cookieStore] = await Promise.all([listWorkspaces(), cookies()]);
  const remembered = cookieStore.get(WORKSPACE_COOKIE)?.value;
  const target = workspaces.find((w) => w.id === remembered) ?? workspaces[0];
  if (target) redirect(`/${target.id}`);
  const pending = await listPendingInvites();
  redirect(pending.length > 0 ? "/invites" : "/onboarding");
}
