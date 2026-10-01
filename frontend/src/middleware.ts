import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const sessionToken = request.cookies.get("gapwright_session")?.value;
  const { pathname } = request.nextUrl;

  const isProtectedRoute =
    pathname.startsWith("/syllabi") ||
    pathname.startsWith("/analysis") ||
    pathname.startsWith("/demand") ||
    pathname.startsWith("/policy");

  const isAuthRoute =
    pathname === "/login" || pathname === "/register";

  // If user is accessing a protected route without session cookie -> redirect to login
  if (isProtectedRoute && !sessionToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If user is already authenticated and visits login/register -> redirect to syllabi
  // (allows ?force=true or ?switch=true to allow switching accounts or re-authenticating)
  if (
    isAuthRoute &&
    sessionToken &&
    !request.nextUrl.searchParams.has("force") &&
    !request.nextUrl.searchParams.has("switch")
  ) {
    return NextResponse.redirect(new URL("/syllabi", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/syllabi/:path*",
    "/analysis/:path*",
    "/demand/:path*",
    "/policy/:path*",
    "/login",
    "/register",
  ],
};
