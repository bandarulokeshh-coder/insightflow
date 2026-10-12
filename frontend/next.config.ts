import type { NextConfig } from "next";

/**
 * In dev, proxy /api/* to the FastAPI backend so the browser only ever talks to
 * one origin (works in the sandbox preview and on localhost).
 * Set NEXT_PUBLIC_API_URL instead when the frontend is deployed separately.
 */
const nextConfig: NextConfig = {
  // Allow the sandbox preview host to load dev/HMR resources; without this the
  // preview renders but hot-reload assets are blocked cross-origin.
  allowedDevOrigins: [
    "localhost:3000",
    "127.0.0.1:3000",
    "*.e2b.app",
  ],

  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_URL) return [];
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
};

export default nextConfig;
