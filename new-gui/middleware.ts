import { getSession, isTokenExpiringSoon, refreshSessionTokens, deleteSession } from "@/app/auth/sessions";
import { NextRequest, NextResponse } from "next/server";

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};


const protectedRoutes = ["/dashboard"];
const publicRoutes = ["/", "/login"];

export default async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;

  const { accessToken, refreshToken } = await getSession();

  // 1. Route classification
  const isProtectedRoute = protectedRoutes.some(route => path.startsWith(route));
  const isPublicRoute = publicRoutes.some(route => path === route); // Exact match for public pages

  // 2. Handle public routes
  if (isPublicRoute) {
    if (accessToken) {
      // Logged-in users shouldn't access public pages
      return NextResponse.redirect(new URL("/dashboard", req.nextUrl));
    }
    return NextResponse.next();
  }

  // 3. Handle protected routes
  if (isProtectedRoute) {
    // No access token at all
    if (!accessToken) {
      return NextResponse.redirect(new URL("/login", req.nextUrl));
    }

    else {
      try {
        // Get session through server-only session module
        const { accessToken, refreshToken } = await getSession();

        // Validate access token expiration
        if (!accessToken || !refreshToken) throw new Error("Missing tokens");

        // Attempt automatic refresh 4 minutes before expiration
        const shouldRefresh = await isTokenExpiringSoon(accessToken, 240);

        if (shouldRefresh) {
          // Attempt token refresh if needed
          // console.log("I should refresh!")
          const newTokens = await refreshSessionTokens(refreshToken);
          if (newTokens) {
            const response = NextResponse.next();
            return response;
          }
        }

        return NextResponse.next();
      } catch (error) {
        console.error("Authentication error:", error);
        const response = NextResponse.redirect(new URL("/login", req.nextUrl));
        response.cookies.delete("accessToken");
        response.cookies.delete("refreshToken");
        return response;
      }
    }
  }

} 