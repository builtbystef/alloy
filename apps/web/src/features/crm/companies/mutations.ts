import type { CompanyCreate, CompanyResponse, CompanyUpdate } from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function createCompany(ws: string, body: CompanyCreate): Promise<CompanyResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/companies/", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

export async function updateCompany(
  ws: string,
  id: string,
  body: CompanyUpdate,
): Promise<CompanyResponse> {
  return unwrap(
    await browserApi.PATCH("/workspaces/{workspace_id}/companies/{company_id}", {
      params: { path: { workspace_id: ws, company_id: id } },
      body,
    }),
  );
}

/** Its attachments go with it; contacts and tasks keep, with the link cleared. */
export async function deleteCompany(ws: string, id: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/companies/{company_id}", {
      params: { path: { workspace_id: ws, company_id: id } },
    }),
  );
}
