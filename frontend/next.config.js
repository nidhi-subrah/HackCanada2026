/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
  },
  async rewrites() {
    // BACKEND_URL must point directly to Railway — never to the same Vercel domain
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    // IMPORTANT: use beforeFiles so these rewrites take precedence over the
    // filesystem. Otherwise /auth/callback would be served by the Next.js
    // page at app/auth/callback/page.tsx and the backend OAuth handler would
    // never run, resulting in "Missing authentication session".
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
        {
          source: '/auth/:path*',
          destination: `${backendUrl}/auth/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    }
  },
}
module.exports = nextConfig
