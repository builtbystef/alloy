import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ApiError, tooManyAttempts } from "@/lib/api-error";
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
    if (status !== 404 && status !== 410 && status !== 429) throw ApiError.fromResult(preview);
    const { title, description } = previewFailure(preview);
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
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

function previewFailure(preview: { response: Response }): { title: string; description: string } {
  switch (preview.response.status) {
    case 410:
      return {
        title: "Invitation expired",
        description: "This link has expired. Ask for a new invitation.",
      };
    case 429:
      return {
        title: "Too many attempts",
        description: tooManyAttempts(ApiError.fromResult(preview).retryAfter),
      };
    default:
      return {
        title: "Invitation not found",
        description: "This link was already used, revoked, or never existed.",
      };
  }
}
