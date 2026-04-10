import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        // Intercept all /api calls from the browser natively
        source: '/api/:path*',
        // Proxy them to the backend service
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
