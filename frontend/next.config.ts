// next.config.ts
import type { NextConfig } from "next";

const isStaticExport = process.env.NEXT_OUTPUT === "export";
const isDesktopBuild = process.env.NEXT_DESKTOP === "true";

const normalizedBasePath = (() => {
  const basePath = process.env.NEXT_BASE_PATH?.trim();
  if (!basePath || basePath === "/") return undefined;
  return basePath.startsWith("/") ? basePath : `/${basePath}`;
})();

const trailingSlash =
  process.env.NEXT_TRAILING_SLASH === "true" ||
  (isStaticExport && process.env.NEXT_TRAILING_SLASH !== "false");

const nextConfig: NextConfig = {
  // Enable static export only when explicitly requested (e.g., Electron desktop builds)
  output: isStaticExport ? "export" : undefined,
  basePath: normalizedBasePath,
  // Desktop builds use the app:// custom protocol which handles absolute paths.
  // Non-desktop static exports use "./" for file:// or relative hosting compatibility.
  assetPrefix: process.env.NEXT_ASSET_PREFIX ?? (isStaticExport && !isDesktopBuild ? "./" : undefined),
  turbopack: {
    root: __dirname,
  },
  // Trailing slashes improve file:// compatibility for static exports
  trailingSlash,
  images: { unoptimized: isStaticExport },
};

export default nextConfig;
