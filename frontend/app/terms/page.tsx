import Link from "next/link"
import { Waypoints } from "lucide-react"

export default function TermsPage() {
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
        <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
        <p className="text-xs text-zinc-500 mb-12">Last updated: April 8, 2026</p>

        <div className="space-y-10 text-sm leading-relaxed">
          <section>
            <h2 className="text-base font-semibold text-white mb-3">1. Acceptance of Terms</h2>
            <p>By accessing or using Networkify, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the service.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">2. Description of Service</h2>
            <p>Networkify is a professional networking tool that allows users to upload LinkedIn connection data, visualize their professional network as an interactive graph, discover referral paths to target companies, and generate outreach messages.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">3. User Data</h2>
            <p className="mb-2">You retain full ownership of any data you upload to Networkify, including LinkedIn CSV exports. By uploading data, you grant us a limited licence to process and store it solely to provide the service to you.</p>
            <p>You are responsible for ensuring that any data you upload complies with applicable laws and LinkedIn's terms of service.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">4. Acceptable Use</h2>
            <p className="mb-2">You agree not to:</p>
            <ul className="list-disc list-inside space-y-1 text-zinc-400">
              <li>Use the service for any unlawful purpose</li>
              <li>Upload data you do not have the right to share</li>
              <li>Attempt to reverse-engineer or interfere with the service</li>
              <li>Use the service to send unsolicited communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">5. Limitation of Liability</h2>
            <p>Networkify is provided "as is" without warranties of any kind. We are not liable for any indirect, incidental, or consequential damages arising from your use of the service.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">6. Changes to Terms</h2>
            <p>We may update these terms from time to time. Continued use of the service after changes constitutes acceptance of the new terms.</p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-white mb-3">7. Contact</h2>
            <p>If you have any questions about these terms, please contact us through the Networkify platform.</p>
          </section>
        </div>

        <div className="mt-16 pt-8 border-t border-zinc-800 flex gap-6 text-xs text-zinc-500">
          <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
        </div>
      </main>
    </div>
  )
}
