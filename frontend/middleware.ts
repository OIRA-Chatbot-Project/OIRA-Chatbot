import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/catalog.pdf",            // allow direct PDF access
]);

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) {
    auth().protect();
  }
});

// MUCH SAFER MATCHER — avoids breaking `/`
export const config = {
  matcher: [
    "/((?!_next|.*\\..*|favicon.ico).*)",
  ],
};
