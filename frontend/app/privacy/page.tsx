import Link from "next/link"
import { Waypoints } from "lucide-react"

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0a0a12] text-zinc-300">
      <nav className="px-8 py-6 border-b border-zinc-800/50">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center">
              <Waypoints className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-medium text-white">Networkify</span>
          </Link>
          <Link href="/login" className="text-xs text-zinc-500 hover:text-white transition-colors">
            Back to Sign In
          </Link>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-8 py-16">
        <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
        <p className="text-xs text-zinc-500 mb-12">Last updated: April 8, 2026</p>

        <div className="space-y-10 text-sm leading-relaxed">
          <section>
            <h2 className="text-base font-semibold text-white mb-3">1. Information We Collect</h2>
            <p className="mb-2">We collect the following information when you use Networkify:</p>
            <ul className="list-disc list-inside space-y-1 text-zinc-400">
              <li><strong className="text-zinc-300">Account data:</strong> Name and email address provided via your authentication provider (Auth0)</li>
              <li><strong className="text-zinc-300">Network data:</strong> LinkedIn connection information you voluntarily upload (names, job titles, company names, profile URLs)</li>
              <li><strong className="text-zinc-300">Usage data:</strong> Pages visited, time spent in the app, and outreach messages generated</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">2. How We Use Your Information</h2>
            <ul className="list-disc list-inside space-y-1 text-zinc-400">
              <li>To build and display your professional network graph</li>
              <li>To identify referral paths to companies you search for</li>
              <li>To generate personalised outreach message templates</li>
              <li>To improve and maintain the service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">3. Data Storage</h2>
            <p>Your network data is stored in a secure graph database. We use industry-standard encryption in transit (HTTPS) and at rest. Authentication is handled by Auth0, a trusted identity provider.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">4. Data Sharing</h2>
            <p className="mb-2">We do not sell your personal data. We share data only with:</p>
            <ul className="list-disc list-inside space-y-1 text-zinc-400">
              <li><strong className="text-zinc-300">Auth0:</strong> For authentication and identity management</li>
              <li><strong className="text-zinc-300">Clearbit:</strong> Company domain lookups (company names only, no personal data)</li>
              <li><strong className="text-zinc-300">Logo.dev:</strong> Company logo retrieval (domain names only)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">5. Your Rights</h2>
            <p className="mb-2">You have the right to:</p>
            <ul className="list-disc list-inside space-y-1 text-zinc-400">
              <li>Access the data we hold about you</li>
              <li>Request deletion of your account and all associated data</li>
              <li>Export your data at any time</li>
            </ul>
            <p className="mt-2">To exercise these rights, contact us through the platform.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">6. Cookies</h2>
            <p>We use HttpOnly session cookies solely to keep you logged in. We do not use tracking or advertising cookies. Vercel Analytics may collect anonymised page view data.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">7. Changes to This Policy</h2>
            <p>We may update this policy periodically. We will notify you of significant changes by updating the date at the top of this page.</p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-zinc-800 flex gap-6 text-xs text-zinc-500">
          <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
        </div>
      </main>
    </div>
  )
}
