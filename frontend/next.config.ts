// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // optional: if you do not need the “Image” component or are hosting images statically
  images: { unoptimized: true },
};

export default nextConfig;
