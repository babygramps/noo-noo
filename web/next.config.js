/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for easier deployment
  output: 'standalone',
  
  // Proxy API requests to the backend in development
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;


