import "server-only";

import { api } from "@/lib/api/server-client";
import { isInviteLink } from "@/lib/routes";

/**
 * The invitation a `?next=/invites/{token}` points at. Null when `next` is
 * anything else or the link is no longer good (the invite page says why).
 */
export async function inviteFromNext(
  next: string | string[] | undefined,
): Promise<{ token: string; email: string } | null> {
  if (typeof next !== "string" || !isInviteLink(next)) return null;
  const token = next.slice("/invites/".length).split(/[/?#]/, 1)[0];
  if (!token) return null;
  const preview = await api.GET("/invites/{token}", { params: { path: { token } } });
  return preview.data ? { token, email: preview.data.email } : null;
}
