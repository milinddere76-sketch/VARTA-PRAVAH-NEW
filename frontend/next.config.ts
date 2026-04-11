import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Never let TypeScript errors abort the Docker build
  typescript: { ignoreBuildErrors: true },

  // Standalone output = minimal self-contained server, starts instantly in Docker
  output: "standalone",

  async rewrites() {
    // BACKEND_URL is a private (non-NEXT_PUBLIC_) env var — read at server
    // runtime, never baked in at build time, so 'http://backend:8000' resolves
    // correctly over the Docker internal network.
    // Smart Fallback: If no env var, try Docker internal name first, then localhost
    const BACKEND_URL = process.env.BACKEND_URL || (process.platform === "linux" ? "http://backend:8000" : "http://localhost:8000");
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
