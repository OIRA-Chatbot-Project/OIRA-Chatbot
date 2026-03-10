/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prevent hydration errors and extension conflicts
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
  // Explicit Turbopack config for Next 16+.
  turbopack: {},
};

module.exports = nextConfig;
