import type { ReactNode } from "react";

import { Logo, Wordmark } from "@/components/shared/logo";

/**
 * Auth pages sit flush on the page: the layout strips the Card chrome (ring,
 * fill, padding, footer band) from every card inside it so the same form
 * components read as a plain form here and as a card elsewhere.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-svh items-center justify-center bg-background px-6 py-12">
      <div className="flex w-full max-w-xs flex-col gap-10">
        <div className="flex items-center gap-3">
          <Logo className="size-10" />
          <Wordmark className="text-3xl" />
        </div>
        <div
          className={[
            "w-full",
            "**:data-[slot=card]:overflow-visible **:data-[slot=card]:bg-transparent **:data-[slot=card]:py-0 **:data-[slot=card]:ring-0 **:data-[slot=card]:[--card-spacing:--spacing(6)]",
            "**:data-[slot=card-header]:px-0 **:data-[slot=card-content]:px-0",
            "**:data-[slot=card-footer]:border-0 **:data-[slot=card-footer]:bg-transparent **:data-[slot=card-footer]:p-0",
            "**:data-[slot=card-title]:text-2xl **:data-[slot=card-title]:font-semibold **:data-[slot=card-title]:tracking-tight",
            "**:data-[slot=card-description]:text-base",
          ].join(" ")}
        >
          {children}
        </div>
      </div>
    </main>
  );
}
