import type { ReactNode } from "react";

import { Logo } from "@/components/logo";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-6">
        <div className="flex items-center gap-3">
          <Logo className="size-10" />
          <span className="text-xl font-semibold tracking-tight">Alloy</span>
        </div>
        <div className="w-full">{children}</div>
      </div>
    </main>
  );
}
