import type { ImportKind } from "@alloy/api-client";
import { z } from "zod";

import { parseSearch, type SearchParams } from "@/lib/lists";

export const importKinds = ["contacts", "companies"] as const satisfies readonly ImportKind[];

/** `?kind=` preselects the import kind; anything else means contacts. */
const importSearchSchema = z.object({
  kind: z.enum(importKinds).catch("contacts"),
});

export type ImportSearch = z.output<typeof importSearchSchema>;

export function parseImportSearch(params: SearchParams | URLSearchParams): ImportSearch {
  return parseSearch(importSearchSchema, params);
}
