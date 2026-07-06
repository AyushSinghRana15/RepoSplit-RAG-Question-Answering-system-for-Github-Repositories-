// Next.js config — legacy URL redirects only
// API proxying is handled by route handlers in app/api/

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Redirect old /website/* routes to home
  async redirects() {
    return [
      {
        source: "/website",
        destination: "/",
        permanent: true,
      },
      {
        source: "/website/:path*",
        destination: "/",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
