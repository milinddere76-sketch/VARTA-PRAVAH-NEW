import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Intercept all /api calls from the browser natively
        source: '/api/:path*',
        // Proxy them to localhost:8000 for development (when running outside Docker)
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

export default nextConfig;
