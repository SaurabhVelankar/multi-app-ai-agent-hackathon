import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
