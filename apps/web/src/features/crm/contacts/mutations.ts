import type {
  ActivityCreate,
  ActivityResponse,
  ContactCreate,
  ContactResponse,
  ContactUpdate,
} from "@alloy/api-client";

import { browserApi } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export async function createContact(ws: string, body: ContactCreate): Promise<ContactResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/contacts/", {
      params: { path: { workspace_id: ws } },
      body,
    }),
  );
}

export async function updateContact(
  ws: string,
  id: string,
  body: ContactUpdate,
): Promise<ContactResponse> {
  return unwrap(
    await browserApi.PATCH("/workspaces/{workspace_id}/contacts/{contact_id}", {
      params: { path: { workspace_id: ws, contact_id: id } },
      body,
    }),
  );
}

/** Its activities and attachments go with it; tasks keep, with the link cleared. */
export async function deleteContact(ws: string, id: string): Promise<void> {
  unwrap(
    await browserApi.DELETE("/workspaces/{workspace_id}/contacts/{contact_id}", {
      params: { path: { workspace_id: ws, contact_id: id } },
    }),
  );
}

/** A call, email, meeting, or follow-up also marks the contact as contacted now. */
export async function logActivity(
  ws: string,
  contactId: string,
  body: ActivityCreate,
): Promise<ActivityResponse> {
  return unwrap(
    await browserApi.POST("/workspaces/{workspace_id}/contacts/{contact_id}/activities", {
      params: { path: { workspace_id: ws, contact_id: contactId } },
      body,
    }),
  );
}
