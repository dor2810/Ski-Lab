import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export: this is a client-rendered SPA that talks to the
  // separately-deployed FastAPI backend over fetch(), so there's no
  // Node server needed here -- Render serves it as a static site,
  // same as the plain-HTML frontend/app it replaces. See
  // frontend/web/README-DEPLOY.md.
  output: "export",
  // No Vercel image-optimization backend exists for a static export;
  // this serves images as-is instead of requiring a custom loader.
  images: { unoptimized: true },
};

export default nextConfig;
