import type { CompanySort } from "@alloy/api-client";
import { z } from "zod";

import { listSearch, optionalParam, parseSearch, type SearchParams } from "@/lib/lists";
import { optionalNotes, optionalText, optionalWebsite, requiredText, text } from "@/lib/validation";

export const companySorts = [
  "name",
  "industry",
  "created_at",
] as const satisfies readonly CompanySort[];

export const companySchema = z.object({
  name: requiredText("Name", 200),
  website: optionalWebsite,
  industry: optionalText(100),
  notes: optionalNotes,
});

export type CompanyInput = z.input<typeof companySchema>;

const companySearchSchema = z.object({
  q: optionalParam(text.min(1)),
  ...listSearch(companySorts),
});

export type CompanySearch = z.output<typeof companySearchSchema>;

export function parseCompanySearch(params: SearchParams | URLSearchParams): CompanySearch {
  return parseSearch(companySearchSchema, params);
}
