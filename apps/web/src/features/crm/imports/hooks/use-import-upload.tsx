"use client";

import type { ImportKind } from "@alloy/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { uploadImport } from "@/features/crm/imports/mutations";
import { errorMessage } from "@/lib/api/errors";
import { IMPORT_MAX_BYTES } from "@/features/crm/imports/limits";
import { formatBytes } from "@/lib/formatting/bytes";
import { importKeys } from "@/features/crm/imports/queries";
import { useWorkspace } from "@/features/workspaces/workspace-provider";

/**
 * One upload at a time; `fraction` is 0..1 while the bytes are in flight and 1
 * while the API confirms and queues the import. Files over the limit are
 * refused before anything is sent.
 */
export function useImportUpload(): {
  start: (kind: ImportKind, file: File) => void;
  fraction: number | null;
} {
  const queryClient = useQueryClient();
  const { id: workspaceId } = useWorkspace();
  const [fraction, setFraction] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: ({ kind, file }: { kind: ImportKind; file: File }) =>
      uploadImport(workspaceId, kind, file, setFraction),
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
