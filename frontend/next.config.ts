// next.config.ts
import type { NextConfig } from "next";

const isStaticExport = process.env.NEXT_OUTPUT === "export";

const normalizedBasePath = (() => {
  const basePath = process.env.NEXT_BASE_PATH?.trim();
  if (!basePath) return undefined;
  return basePath.startsWith("/") ? basePath : `/${basePath}`;
})();

const trailingSlash =
  process.env.NEXT_TRAILING_SLASH === "true" ||
  (isStaticExport && process.env.NEXT_TRAILING_SLASH !== "false");

const nextConfig: NextConfig = {
  // Enable static export only when explicitly requested (e.g., Tauri bundles)
  output: isStaticExport ? "export" : undefined,
  basePath: normalizedBasePath,
  assetPrefix: process.env.NEXT_ASSET_PREFIX ?? (isStaticExport ? "./" : undefined),
  // Trailing slashes improve file:// compatibility for static exports
  trailingSlash,
  images: { unoptimized: isStaticExport },
};

export default nextConfig;
