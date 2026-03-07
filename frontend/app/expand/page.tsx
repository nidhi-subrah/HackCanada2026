"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"
import { Network, FileText, ArrowRight, Shield, CheckCircle2, Loader2, AlertCircle, Upload } from "lucide-react"
import Sidebar from "@/components/Sidebar"
import { useAuth } from "@/components/AuthContext"


export default function ExpandPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  
  // These fields are specifically for the new CSV being uploaded
  const [ownerName, setOwnerName] = useState("")
  const [ownerEmail, setOwnerEmail] = useState("")
  
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle")
  const [result, setResult] = useState<any>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleUpload = async () => {
    if (!file || !ownerName) return
    setStatus("loading")
    const formData = new FormData()
    formData.append("file", file)

    // Send owner metrics to the backend, so the graph links it to the right person
    let url = `${process.env.NEXT_PUBLIC_API_URL}/api/upload/csv?user_name=${encodeURIComponent(ownerName)}`
    if (ownerEmail) {
      url += `&user_email=${encodeURIComponent(ownerEmail)}`
    }

    try {
      const res = await axios.post(
        url,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      )
      setResult(res.data)
      setStatus("done")
      
      // Deliberately NOT overriding localStorage user_id or user_name here
      // because we want the primary user session to remain the main identity!
      
    } catch (e) {
      console.error(e)
      setStatus("error")
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  return (
    <div className="flex min-h-screen bg-dark-bg">
      <Sidebar />

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg animate-fade-in">
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center mx-auto mb-6 shadow-glow">
            <Network className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-3">Expand Your Network</h1>
          <p className="text-zinc-400">
            Upload another person's connections to find multi-degree paths
          </p>
        </div>

        {status === "done" ? (
          <div className="glass-card p-8 border-accent-emerald/30 animate-slide-up">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-accent-emerald/10 border border-accent-emerald/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 className="w-8 h-8 text-accent-emerald" />
              </div>
              <h2 className="text-2xl font-semibold text-white mb-2">Network Expanded!</h2>
              <p className="text-zinc-400 mb-8">
                {result ? result.message : "Their connections have been seamlessly linked to your master graph."}
              </p>
              
              <div className="grid gap-4">
                <button 
                  onClick={() => router.push("/graph")} 
                  className="btn-primary"
                >
                  View Multi-Hop Graph
                </button>
                <button 
                  onClick={() => {
                    setFile(null);
                    setOwnerName("");
                    setOwnerEmail("");
                    setStatus("idle");
                  }} 
                  className="btn-secondary"
                >
                  Upload Another
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-card p-8 space-y-6">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Connection Owner Name
              </label>
              <input
                type="text"
                placeholder="Name of the person who exported this CSV"
                value={ownerName}
                onChange={e => setOwnerName(e.target.value)}
                className="input-field w-full px-4 py-3 bg-dark-bg/50 border border-dark-glassBorder rounded-xl text-white outline-none focus:border-brand-500 transition-colors"
                autoComplete="off"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Connection Owner Email (Optional)
              </label>
              <input
                type="email"
                placeholder="To link them directly if they're already in your network"
                value={ownerEmail}
                onChange={e => setOwnerEmail(e.target.value)}
                className="input-field w-full px-4 py-3 bg-dark-bg/50 border border-dark-glassBorder rounded-xl text-white outline-none focus:border-brand-500 transition-colors"
                autoComplete="off"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Their Connections CSV
              </label>
              <label 
                className={`
                  relative flex flex-col items-center justify-center p-10 border-2 border-dashed rounded-xl 
                  cursor-pointer transition-all duration-200
                  ${dragActive 
                    ? "border-brand-500 bg-brand-500/10" 
                    : file 
                      ? "border-accent-emerald/50 bg-accent-emerald/5" 
                      : "border-dark-glassBorder hover:border-zinc-600 hover:bg-dark-elevated/50"
                  }
                `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input 
                  type="file" 
                  accept=".csv" 
                  className="hidden" 
                  onChange={e => setFile(e.target.files?.[0] || null)} 
                />
                
                {file ? (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
                      <FileText className="w-5 h-5 text-accent-emerald" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium break-all max-w-[200px]">{file.name}</p>
                      <p className="text-sm text-zinc-500">Click or drag to replace</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className={`w-8 h-8 mb-3 transition-colors ${dragActive ? "text-brand-400" : "text-zinc-500"}`} />
                    <p className="text-zinc-300 font-medium mb-1">
                      Drop their CSV here
                    </p>
                    <p className="text-sm text-zinc-500">Connections.csv from their LinkedIn</p>
                  </>
                )}
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || !ownerName || status === "loading"}
              className="btn-primary w-full py-4 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            >
              {status === "loading" ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Expanding Network...
                </>
              ) : (
                <>
                  Expand Network
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
              <Shield className="w-4 h-4 text-accent-emerald" />
              <span>Network graphs map privately without notifications</span>
            </div>
          </div>
        )}

          <div className="mt-8 p-4 rounded-xl bg-dark-surface/50 border border-dark-glassBorder">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-accent-brand mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="text-zinc-300 font-medium mb-1">Building Multi-Hop Paths</p>
                <p className="text-zinc-500">
                  By uploading a friend or colleague's connections, the AI will string together 2nd and 3rd degree referral paths to your target companies.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
