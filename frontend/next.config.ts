import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Never let TypeScript or ESLint errors abort the Docker build
  typescript: { ignoreBuildErrors: true },
  eslint:     { ignoreDuringBuilds: true },

  async rewrites() {
    // IMPORTANT: Use BACKEND_URL (private, non-NEXT_PUBLIC_) so it's read
    // at server runtime, not baked in at build time when value is undefined.
    const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
