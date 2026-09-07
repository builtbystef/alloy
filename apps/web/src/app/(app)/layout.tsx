import { Suspense, type ReactNode } from "react";

import { TimeZoneSync } from "@/components/time-zone-sync";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { getTimeZone } from "@/lib/time-zone";

import { AppSidebar } from "./app-sidebar";

/**
 * The shell is static and prerendered. The sidebar's dynamic parts (nav
 * highlight, user menu) stream in behind their own <Suspense> boundaries.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
          <span className="text-sm font-medium md:hidden">Alloy CRM</span>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-6 md:py-8">{children}</main>
      </SidebarInset>
      <Suspense>
        <CurrentTimeZone />
      </Suspense>
    </SidebarProvider>
  );
}

async function CurrentTimeZone() {
  return <TimeZoneSync serverTimeZone={await getTimeZone()} />;
}
