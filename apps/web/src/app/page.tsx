import { Suspense } from "react";

import { ApiStatus } from "./api-status";

export default function Page() {
  return (
    <main>
      <h1>Alloy</h1>
      <p>Next.js talking to FastAPI through the typed client in packages/api-client.</p>
      <Suspense fallback={<p>Checking API…</p>}>
        <ApiStatus />
      </Suspense>
    </main>
  );
}
