/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: "/dashboard",
        destination: "/",
        permanent: false,
      },
      {
        source: "/home",
        destination: "/",
        permanent: false,
      },
      {
        source: "/forecast",
        destination: "/",
        permanent: false,
      },
      {
        source: "/forecasts",
        destination: "/",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
