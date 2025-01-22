import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { deleteSession, refreshSession } from "./app/auth/sessions";
import { jwtDecode } from "./lib/utils";

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

// 1. specify which routes are public and private

const protectedRoutes = ["/dashboard"];

const publicRoutes = ["/", "/login"];

export default async function middleware(req: NextRequest) {
  // 2. check if the current route is protected or public

  const path = req.nextUrl.pathname;

  const isProtectedRoute = protectedRoutes.includes(path);
  const isPublicRoute = publicRoutes.includes(path);

  // 3. check session in cookie

  const accessToken = req.cookies.get("accessToken")?.value;

  const isAuth = !!accessToken;

  // 4. Redirect

  if (isProtectedRoute && !isAuth) {
    return NextResponse.redirect(new URL("/login", req.nextUrl));
  }

  if (
    isPublicRoute &&
    isAuth &&
    !req.nextUrl.pathname.startsWith("/dashboard")
  ) {
    return NextResponse.redirect(new URL("/dashboard", req.nextUrl));
  }

  // 5 Refresh any existing tokens
  if (!accessToken) {
    // console.log("no token found")
    // return NextResponse.next();
  }

  if (accessToken) {
    // console.log("token found")

    const decoded = jwtDecode(accessToken); // This function decodes JWT, no libraries needed
    // console.log(decoded)
    // Check if the access token has expired (check exp timestamp)
    console.log(
      decoded.exp * 1000,
      Date.now(),
      decoded.exp * 1000 < Date.now(),
    );
    // if token is expired, then return to login

    if (decoded.exp * 1000 < Date.now()) {
      deleteSession();
      return NextResponse.redirect(new URL("/login", req.url));
    } else {
      // If not, keep session fresh boi!
      const refreshResult = await refreshSession();

      // If refresh is successful, retry the request
      if (refreshResult.success) {
        // We don't need to do anything further; the `refreshSession` function already updates cookies
        // const newAccessToken = (await cookies()).get('accessToken')?.value;
        console.log("refreshed");
        // Set the new access token in the request headers before forwarding
        // req.headers.set('Authorization', `Bearer ${newAccessToken}`);
      }
    }
  }

  return NextResponse.next();
}
