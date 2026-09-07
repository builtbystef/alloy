import Link from "next/link";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";

export default function RootNotFound() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-6">
      <Logo className="size-12" />
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <Button variant="outline" nativeButton={false} render={<Link href="/" />}>
        Back to Alloy
      </Button>
    </main>
  );
}
