import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SESSION_COOKIE } from "@/lib/session";

/**
 * Clears a session cookie the API no longer accepts (expired, or revoked by
 * "log out everywhere" on another device), then goes to the login page.
 *
 * Without this a stale cookie is a trap: `proxy.ts` keeps `/login` away from
 * anyone holding a cookie, and every app page sends the holder of an invalid
 * one to `/login`. Deleting needs the same attributes the API set the
 * `__Host-` cookie with, or the browser ignores the deletion.
 */
export async function GET(): Promise<never> {
  (await cookies()).delete({ name: SESSION_COOKIE, path: "/", secure: true });
  redirect("/login");
}
