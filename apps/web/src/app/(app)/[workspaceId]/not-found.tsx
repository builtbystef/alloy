import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-start gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">Not found</h1>
      <p className="text-muted-foreground">
        This record or workspace does not exist, or you are not a member of it.
      </p>
      <Button variant="outline" nativeButton={false} render={<Link href="/" />}>
        Back to your workspaces
      </Button>
    </div>
  );
}
