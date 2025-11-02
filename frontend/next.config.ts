// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // optional: falls du “Image” nicht brauchst oder statisch hostest
  images: { unoptimized: true }
};

export default nextConfig;
