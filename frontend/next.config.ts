import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Intercept all /api calls from the browser natively
        source: '/api/:path*',
        // Proxy them behind impenetrable Docker local subnets straight to FastAPI!
        destination: 'http://backend:8000/:path*',
      },
    ];
  },
};

export default nextConfig;
