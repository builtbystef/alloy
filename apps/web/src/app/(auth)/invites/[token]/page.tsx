import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import { getCurrentUser } from "@/lib/session";

import { AcceptInvite } from "./accept-invite";

export const metadata: Metadata = { title: "Invitation" };

type Params = Promise<{ token: string }>;

/**
 * The link from the invitation email. The preview needs no login; accepting
 * does, and the proxy sends logged-out visitors to /login?next=... first.
 */
export default function InvitePage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <InviteContent params={params} />
    </Suspense>
  );
}

async function InviteContent({ params }: { params: Params }) {
  const { token } = await params;
  const [preview, user] = await Promise.all([
    api.GET("/invites/{token}", { params: { path: { token } } }),
    getCurrentUser(),
  ]);

  if (!preview.data) {
    const status = preview.response.status;
    if (status !== 404 && status !== 410) throw ApiError.fromResult(preview);
    return (
      <Card>
        <CardHeader>
          <CardTitle>{status === 410 ? "Invitation expired" : "Invitation not found"}</CardTitle>
          <CardDescription>
            {status === 410
              ? "This link has expired. Ask for a new invitation."
              : "This link was already used, revoked, or never existed."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" nativeButton={false} render={<Link href="/" />}>
            Go to your workspaces
          </Button>
        </CardContent>
      </Card>
    );
  }

  return <AcceptInvite token={token} invite={preview.data} userEmail={user?.email ?? null} />;
}
