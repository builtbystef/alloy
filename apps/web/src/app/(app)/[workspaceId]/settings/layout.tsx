import { Suspense, type ReactNode } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { SettingsNav, SettingsNavFallback } from "@/features/workspaces/components/settings-nav";

/** Every workspace settings page shares the header and the secondary nav. */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <PageHeader
        title="Workspace settings"
        description="Its name, its people, and what they may do."
      />
      <div className="flex flex-col gap-6 md:flex-row md:gap-12">
        <aside className="shrink-0 md:w-44">
          <Suspense fallback={<SettingsNavFallback />}>
            <SettingsNav />
          </Suspense>
        </aside>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </>
  );
}
