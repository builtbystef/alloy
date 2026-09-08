import type { NextRequest } from "next/server";

import { getApiUrl } from "@/lib/api";

/**
 * Forwards `/api/*` to the FastAPI service, so the browser never needs the
 * API's address or a CORS setup: the session cookie the API sets on login
 * comes back through this handler and is stored for the Next.js origin, and
 * every later request carries it here, where it is forwarded upstream.
 *
 * Only the headers that matter cross the boundary. Hop-by-hop headers and
 * anything the API does not need stay on their side. The visitor's address
 * goes along as `X-Forwarded-For`, which the API's rate limits key on.
 */
const REQUEST_HEADERS = ["accept", "content-type", "cookie"];
const RESPONSE_HEADERS = ["content-type", "cache-control", "location", "retry-after"];

/**
 * The visitor's address as the platform in front reports it. The last
 * `X-Forwarded-For` entry is the one the nearest proxy appended, so it is the
 * one a visitor cannot forge. Null with nothing in front (local `next dev`);
 * the API then sees this server's address.
 */
function clientAddress(request: NextRequest): string | null {
  const direct = request.headers.get("cf-connecting-ip") ?? request.headers.get("x-real-ip");
  if (direct) return direct.trim();
  const forwarded = request.headers.get("x-forwarded-for");
  if (!forwarded) return null;
  const last = forwarded.split(",").at(-1)?.trim();
  return last || null;
}

async function proxy(request: NextRequest): Promise<Response> {
  const { pathname, search } = request.nextUrl;
  const target = new URL(pathname.replace(/^\/api/, "") + search, getApiUrl());

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  const address = clientAddress(request);
  if (address !== null) headers.set("x-forwarded-for", address);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : null,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value !== null) responseHeaders.set(name, value);
  }
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }

  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export { proxy as DELETE, proxy as GET, proxy as PATCH, proxy as POST, proxy as PUT };
