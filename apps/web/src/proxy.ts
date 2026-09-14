import { NextResponse, type NextRequest } from "next/server";

/**
 * Cheap routing on the session cookie's presence: no cookie, no app pages;
 * a cookie, no login pages. Whether the cookie is still valid, and whether the
 * email is verified, is the API's call, made by `requireUser()` in each page.
 */
const SESSION_COOKIE = "__Host-session";
const AUTH_PATHS = ["/login", "/signup"];
const OPEN_PATHS = [
  "/verify-email",
  "/confirm-email",
  "/forgot-password",
  "/reset-password",
  "/logout",
];
// Invitation links preview without a login; the `/invites` list needs one.
const OPEN_PREFIXES = ["/invites/"];

const matches = (paths: string[], pathname: string) =>
  paths.some((path) => pathname === path || pathname === `${path}/`);

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const isAuthPath = matches(AUTH_PATHS, pathname);

  if (
    matches(OPEN_PATHS, pathname) ||
    OPEN_PREFIXES.some((prefix) => pathname.length > prefix.length && pathname.startsWith(prefix))
  ) {
    return NextResponse.next();
  }
  if (!hasSession && !isAuthPath) {
    const login = new URL("/login", request.url);
    // The whole location, so a filtered list survives the login.
    const next = pathname + search;
    if (next !== "/") login.searchParams.set("next", next);
    return NextResponse.redirect(login);
  }
  if (hasSession && isAuthPath) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except the API proxy, Next.js internals, and static files.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
