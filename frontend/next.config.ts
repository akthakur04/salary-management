import type { NextConfig } from "next";

/**
 * The browser only talks to this origin: /api/* is proxied to FastAPI, so the
 * session cookie stays first-party and no CORS is needed (ARCHITECTURE §1).
 */
const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
