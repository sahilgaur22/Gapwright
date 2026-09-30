import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const sessionToken = request.cookies.get("gapwright_session")?.value;
  const { pathname } = request.nextUrl;

  const isProtectedRoute =
    pathname.startsWith("/syllabi") ||
    pathname.startsWith("/analysis");

  const isAuthRoute =
    pathname === "/login" || pathname === "/register";

  // If user is accessing a protected route without session cookie -> redirect to login
  if (isProtectedRoute && !sessionToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If user is already authenticated and visits login/register -> redirect to syllabi
  if (isAuthRoute && sessionToken) {
    return NextResponse.redirect(new URL("/syllabi", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/syllabi/:path*",
    "/analysis/:path*",
    "/login",
    "/register",
  ],
};
