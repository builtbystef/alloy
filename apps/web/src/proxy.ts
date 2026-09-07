import { NextResponse, type NextRequest } from "next/server";

/**
 * Cheap routing on the session cookie's presence: no cookie, no app pages;
 * a cookie, no login pages. Whether the cookie is still valid is the API's
 * call, made by `requireUser()` in each page.
 */
const SESSION_COOKIE = "__Host-session";
const AUTH_PATHS = ["/login", "/signup"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const isAuthPath = AUTH_PATHS.some((path) => pathname === path || pathname === `${path}/`);

  if (!hasSession && !isAuthPath) {
    const login = new URL("/login", request.url);
    if (pathname !== "/") login.searchParams.set("next", pathname);
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
