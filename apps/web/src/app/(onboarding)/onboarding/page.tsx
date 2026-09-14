import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listWorkspaces } from "@/features/workspaces/server";

import { CreateWorkspaceForm } from "@/features/workspaces/components/create-workspace-form";
import { OnboardingSteps } from "@/features/workspaces/components/onboarding-steps";

export const metadata: Metadata = { title: "New workspace" };

/** Step one: the name. Reached from `/` the first time, from the switcher after. */
export default function OnboardingPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <OnboardingContent />
    </Suspense>
  );
}

async function OnboardingContent() {
  const workspaces = await listWorkspaces();
  const first = workspaces.length === 0;
  return (
    <Card>
      <CardHeader>
        <OnboardingSteps current={1} />
        <CardTitle>{first ? "Name your workspace" : "New workspace"}</CardTitle>
        <CardDescription>
          {first
            ? "A workspace holds your contacts, companies, and tasks, and the people you work with. Your company's name works well."
            : "A separate set of contacts, companies, and tasks, with its own members. You will be its owner."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-8">
        <CreateWorkspaceForm />
        {first ? (
          <div className="flex flex-col gap-1 border-t pt-6 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Joining a team instead?</p>
            <p>
              You do not need a workspace of your own. Ask an admin of your team's workspace to
              invite you: the link in that email adds you to it. Invitations for{" "}
              <span className="text-foreground">your address</span> also appear here and in your
              account settings once sent.
            </p>
          </div>
        ) : (
          <Button
            variant="ghost"
            className="self-start"
            nativeButton={false}
            render={<Link href="/" />}
          >
            Cancel
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
