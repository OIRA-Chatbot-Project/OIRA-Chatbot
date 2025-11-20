/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prevent hydration errors and extension conflicts
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
  // Handle browser extension conflicts
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Ignore chrome extension errors in browser
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
