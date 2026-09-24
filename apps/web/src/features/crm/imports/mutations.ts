import type { ImportKind, ImportResponse } from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { putFile } from "@/lib/api/upload";

/** What the upload URL is signed for; the browser's own guess for `.csv` varies. */
const CSV_CONTENT_TYPE = "text/csv";

/**
 * Import a CSV: ask the API for an upload URL, `PUT` the file straight to
 * storage, then tell the API to start the job. `onProgress` gets 0..1 while
 * the bytes are in flight and 1 while the API confirms and queues the import.
 */
export async function uploadImport(
  ws: string,
  kind: ImportKind,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<ImportResponse> {
  const ticket = unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/imports/", {
      params: { path: { workspace_id: ws } },
      body: { kind, filename: file.name, size: file.size },
    }),
  );
  await putFile(ticket.upload_url, file, CSV_CONTENT_TYPE, onProgress);
  onProgress(1);
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/imports/{import_id}/start", {
      params: { path: { workspace_id: ws, import_id: ticket.import.id } },
    }),
  );
}
