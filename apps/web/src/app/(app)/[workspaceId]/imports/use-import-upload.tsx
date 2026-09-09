"use client";

import type { ImportKind, ImportRead } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { browserApi } from "@/lib/api-browser";
import { errorMessage, unwrap } from "@/lib/api-error";
import { IMPORT_MAX_BYTES, formatBytes } from "@/lib/bytes";
import { importKeys } from "@/lib/queries";
import { putFile } from "@/lib/upload";
import { useWorkspace } from "@/lib/workspace";

/** What the upload URL is signed for; the browser's own guess for `.csv` varies. */
const CSV_CONTENT_TYPE = "text/csv";

/**
 * The same three steps as an attachment: ask the API for an upload URL, `PUT`
 * the file straight to storage, then tell the API to start the job. One
 * upload at a time; `fraction` is 0..1 while the bytes are in flight and 1
 * while the API confirms and queues the import.
 */
export function useImportUpload(): {
  start: (kind: ImportKind, file: File) => void;
  fraction: number | null;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [fraction, setFraction] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: async ({ kind, file }: { kind: ImportKind; file: File }): Promise<ImportRead> => {
      const ticket = unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/imports/", {
          params: { path: { workspace_id: workspaceId } },
          body: { kind, filename: file.name, size: file.size },
        }),
      );
      await putFile(ticket.upload_url, file, CSV_CONTENT_TYPE, setFraction);
      setFraction(1);
      return unwrap(
        await browserApi.POST("/workspaces/{workspace_id}/imports/{import_id}/start", {
          params: { path: { workspace_id: workspaceId, import_id: ticket.import.id } },
        }),
      );
    },
    onSuccess: async (record) => {
      toast.success(`${record.filename} is queued; the rows appear as it runs.`);
      await queryClient.invalidateQueries({ queryKey: importKeys.lists(workspaceId) });
    },
    onError: (error, { file }) => toast.error(`${file.name}: ${errorMessage(error)}`),
    onSettled: () => setFraction(null),
  });

  const start = (kind: ImportKind, file: File) => {
    if (file.size > IMPORT_MAX_BYTES) {
      toast.error(
        `${file.name} is ${formatBytes(file.size)}; the limit is ${formatBytes(IMPORT_MAX_BYTES)}.`,
      );
      return;
    }
    setFraction(0);
    mutation.mutate({ kind, file });
  };

  return { start, fraction };
}
