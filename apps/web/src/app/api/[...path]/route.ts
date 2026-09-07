import type { NextRequest } from "next/server";

import { getApiUrl } from "@/lib/api";

/**
 * Forwards `/api/*` to the FastAPI service, so the browser never needs the
 * API's address or a CORS setup: the session cookie the API sets on login
 * comes back through this handler and is stored for the Next.js origin, and
 * every later request carries it here, where it is forwarded upstream.
 *
 * Only the headers that matter cross the boundary. Hop-by-hop headers and
 * anything the API does not need stay on their side.
 */
const REQUEST_HEADERS = ["accept", "content-type", "cookie"];
const RESPONSE_HEADERS = ["content-type", "cache-control", "location"];

async function proxy(request: NextRequest): Promise<Response> {
  const { pathname, search } = request.nextUrl;
  const target = new URL(pathname.replace(/^\/api/, "") + search, getApiUrl());

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }

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
