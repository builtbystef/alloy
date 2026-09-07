import { Suspense } from "react";

import { Button } from "@/components/ui/button";

import { ApiStatus } from "./api-status";

export default function Page() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Alloy</h1>
      <p className="text-muted-foreground">
        Next.js talking to FastAPI through the typed client in packages/api-client.
      </p>
      <Suspense fallback={<p>Checking API…</p>}>
        <ApiStatus />
      </Suspense>
      <div className="flex gap-2">
        <Button>Primary</Button>
        <Button variant="outline">Outline</Button>
      </div>
    </main>
  );
}
