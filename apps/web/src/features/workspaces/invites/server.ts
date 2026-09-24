import "server-only";

import type { PendingInviteResponse } from "@alloy/api-client";

import { ApiError } from "@/lib/api/errors";
import { api } from "@/lib/api/server-client";
import { getSessionApi, requireUser } from "@/features/auth/server";
import { isInviteLink } from "@/lib/routes";

/** The caller's own, for Server Components. */
export async function listPendingInvites(): Promise<PendingInviteResponse[]> {
  await requireUser();
  const sessionApi = await getSessionApi();
  const result = await sessionApi.GET("/invites/pending");
  if (result.data) return result.data;
  throw ApiError.fromResult(result);
}

/** The public preview of an emailed link: the raw result, since the page reads the status. */
export function previewInvite(token: string) {
  return api.GET("/invites/{token}", { params: { path: { token } } });
}

/**
 * The invitation a `?next=/invites/{token}` points at, for the login and
 * sign-up pages. Null when `next` is anything else or the link is no longer
 * good (the invite page says why).
 */
export async function inviteFromNext(
  next: string | string[] | undefined,
): Promise<{ token: string; email: string } | null> {
  if (typeof next !== "string" || !isInviteLink(next)) return null;
  const token = next.slice("/invites/".length).split(/[/?#]/, 1)[0];
  if (!token) return null;
  const preview = await previewInvite(token);
  return preview.data ? { token, email: preview.data.email } : null;
}
