import type { NextConfig } from "next";

// Where the Accura API lives when the browser calls this app's own
// /api/v1 (i.e. NEXT_PUBLIC_API_URL is not set). Evaluated at build time.
const backendUrl = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_URL) return [];
    return [{ source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*` }];
  },
};

export default nextConfig;
