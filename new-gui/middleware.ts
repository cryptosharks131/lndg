// import { NextRequest, NextResponse } from "next/server";
// import { deleteSession, refreshSession } from "./app/auth/sessions";
// import { jwtDecode } from "./lib/utils";

// export const config = {
//   matcher: [
//     /*
//      * Match all request paths except for the ones starting with:
//      * - api (API routes)
//      * - _next/static (static files)
//      * - _next/image (image optimization files)
//      * - favicon.ico, sitemap.xml, robots.txt (metadata files)
//      */
//     "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
//   ],
// };


// // 1. specify which routes are public and private

// const protectedRoutes = ["/dashboard"];

// const publicRoutes = ["/", "/login"];

// export default async function middleware(req: NextRequest) {
//   // 2. check if the current route is protected or public

//   const path = req.nextUrl.pathname;

//   const isProtectedRoute = protectedRoutes.includes(path);
//   const isPublicRoute = publicRoutes.includes(path);

//   // 3. check session in cookie

//   const accessToken = req.cookies.get("accessToken")?.value;

//   const isAuth = !!accessToken;

//   // 4. Redirect

//   // deactivating for dev env 


//   if (isProtectedRoute && !isAuth) {
//     return NextResponse.redirect(new URL("/login", req.nextUrl));
//   }

//   if (
//     isPublicRoute &&
//     isAuth &&
//     !req.nextUrl.pathname.startsWith("/dashboard")
//   ) {
//     return NextResponse.redirect(new URL("/dashboard", req.nextUrl));
//   }

//   // 5 Refresh any existing tokens
//   if (!accessToken) {
//     // console.log("no token found")
//     // return NextResponse.next();
//   }

//   if (accessToken) {
//     // console.log("token found")

//     const decoded = jwtDecode(accessToken); // This function decodes JWT, no libraries needed
//     // console.log(decoded)
//     // Check if the access token has expired (check exp timestamp)
//     // console.log(
//     //   decoded.exp * 1000,
//     //   Date.now(),
//     //   decoded.exp * 1000 < Date.now(),
//     // );
//     // if token is expired, then return to login

//     if (decoded.exp * 1000 < Date.now()) {
//       deleteSession();
//       return NextResponse.redirect(new URL("/login", req.url));
//     } else {
//       // If not, keep session fresh boi!
//       const refreshResult = await refreshSession();

//       // If refresh is successful, retry the request
//       if (refreshResult.success) {
//         // We don't need to do anything further; the `refreshSession` function already updates cookies
//         // const newAccessToken = (await cookies()).get('accessToken')?.value;
//         console.log("refreshed");
//         // Set the new access token in the request headers before forwarding
//         // req.headers.set('Authorization', `Bearer ${newAccessToken}`);
//       }
//     }
//   }

//   return NextResponse.next();
// }


import { NextRequest, NextResponse } from "next/server";
import { getSession, refreshSessionTokens, deleteSession, isTokenExpiringSoon } from "@/app/auth/sessions";

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

        // Attempt automatic refresh 1 minute before expiration
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