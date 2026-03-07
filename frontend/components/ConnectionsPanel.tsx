"use client"
import { useState, useEffect, useCallback } from "react"
import axios from "axios"
import {
  X, Upload, FileText, Loader2, CheckCircle2, Trash2,
  UserPlus, Users, Clock, AlertCircle
} from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type ConnectionSource = {
  id: string
  owner_name: string
  owner_email: string
  uploaded_at: string
  connection_count: number
  filename: string
}

type Props = {
  isOpen: boolean
  onClose: () => void
}

export default function ConnectionsPanel({ isOpen, onClose }: Props) {
  const [sources, setSources] = useState<ConnectionSource[]>([])
  const [loading, setLoading] = useState(false)

  // Upload form state
  const [file, setFile] = useState<File | null>(null)
  const [ownerName, setOwnerName] = useState("")
  const [ownerEmail, setOwnerEmail] = useState("")
  const [uploadStatus, setUploadStatus] = useState<"idle" | "loading" | "done" | "error">("idle")
  const [dragActive, setDragActive] = useState(false)

  const fetchSources = useCallback(async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_URL}/api/graph/sources`)
      setSources(res.data.sources)
    } catch (e) {
      console.error("Failed to fetch sources:", e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) fetchSources()
  }, [isOpen, fetchSources])

  const handleUpload = async () => {
    if (!file || !ownerName) return
    setUploadStatus("loading")
    const formData = new FormData()
    formData.append("file", file)

    // Get auth_email from stored user info
    const storedUser = localStorage.getItem("auth_user")
    const authEmail = storedUser ? JSON.parse(storedUser)?.email || "" : ""

    let url = `${API_URL}/api/upload/csv?user_name=${encodeURIComponent(ownerName)}&is_additional=true`
    if (ownerEmail) {
      url += `&user_email=${encodeURIComponent(ownerEmail)}`
    }
    if (authEmail) {
      url += `&auth_email=${encodeURIComponent(authEmail)}`
    }

    try {
      await axios.post(url, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setUploadStatus("done")
      setFile(null)
      setOwnerName("")
      setOwnerEmail("")
      fetchSources()
      // Reset status after a delay
      setTimeout(() => setUploadStatus("idle"), 3000)
    } catch (e) {
      console.error(e)
      setUploadStatus("error")
      setTimeout(() => setUploadStatus("idle"), 3000)
    }
  }

  const handleDelete = async (sourceId: string) => {
    try {
      await axios.delete(`${API_URL}/api/graph/sources/${sourceId}`)
      setSources((prev) => prev.filter((s) => s.id !== sourceId))
    } catch (e) {
      console.error("Failed to delete source:", e)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true)
    else if (e.type === "dragleave") setDragActive(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0])
  }

  const formatDate = (iso: string) => {
    if (!iso) return ""
    try {
      return new Date(iso).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric",
      })
    } catch {
      return iso
    }
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[55] transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 left-[80px] bottom-0 w-[380px] bg-[#18181b] border-r border-dark-glassBorder z-[60] flex flex-col transition-transform duration-300 ease-out ${
          isOpen ? "translate-x-0" : "-translate-x-[460px]"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-glassBorder">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center shadow-glow">
              <UserPlus className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Connections</h2>
              <p className="text-xs text-zinc-500">Add network data sources</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-dark-elevated flex items-center justify-center text-zinc-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          {/* Upload Section */}
          <div className="p-6 border-b border-dark-glassBorder">
            <h3 className="text-sm font-medium text-zinc-300 mb-4 flex items-center gap-2">
              <Upload className="w-4 h-4 text-brand-400" />
              Add New Source
            </h3>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="Connection owner's name"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                className="w-full px-3 py-2.5 bg-dark-bg/60 border border-dark-glassBorder rounded-xl text-sm text-white placeholder-zinc-500 outline-none focus:border-brand-500 transition-colors"
              />
              <input
                type="email"
                placeholder="Email (optional — helps link existing nodes)"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                className="w-full px-3 py-2.5 bg-dark-bg/60 border border-dark-glassBorder rounded-xl text-sm text-white placeholder-zinc-500 outline-none focus:border-brand-500 transition-colors"
              />

              {/* Drop zone */}
              <label
                className={`relative flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 ${
                  dragActive
                    ? "border-brand-500 bg-brand-500/10"
                    : file
                    ? "border-accent-emerald/50 bg-accent-emerald/5"
                    : "border-dark-glassBorder hover:border-zinc-600 hover:bg-dark-elevated/50"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                {file ? (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent-emerald/10 flex items-center justify-center">
                      <FileText className="w-4 h-4 text-accent-emerald" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm text-white font-medium truncate max-w-[200px]">
                        {file.name}
                      </p>
                      <p className="text-xs text-zinc-500">Click to replace</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className={`w-6 h-6 mb-2 ${dragActive ? "text-brand-400" : "text-zinc-500"}`} />
                    <p className="text-sm text-zinc-300">Drop CSV here</p>
                    <p className="text-xs text-zinc-500">connections.csv from their LinkedIn</p>
                  </>
                )}
              </label>

              <button
                onClick={handleUpload}
                disabled={!file || !ownerName || uploadStatus === "loading"}
                className="btn-primary w-full py-2.5 text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {uploadStatus === "loading" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : uploadStatus === "done" ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Added!
                  </>
                ) : uploadStatus === "error" ? (
                  <>
                    <AlertCircle className="w-4 h-4" />
                    Failed — try again
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    Add Connections
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Sources List */}
          <div className="p-6">
            <h3 className="text-sm font-medium text-zinc-300 mb-4 flex items-center gap-2">
              <Users className="w-4 h-4 text-accent-cyan" />
              Uploaded Sources
              {sources.length > 0 && (
                <span className="ml-auto text-xs text-zinc-500 bg-dark-elevated px-2 py-0.5 rounded-full">
                  {sources.length}
                </span>
              )}
            </h3>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-zinc-500 animate-spin" />
              </div>
            ) : sources.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                <p className="text-sm text-zinc-500">No sources yet</p>
                <p className="text-xs text-zinc-600 mt-1">
                  Upload a friend&apos;s connections.csv to expand your network graph
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {sources.map((source) => (
                  <div
                    key={source.id}
                    className="group flex items-center gap-3 p-3 rounded-xl bg-dark-bg/40 border border-dark-glassBorder hover:border-zinc-700 transition-all"
                  >
                    <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-cyan/20 to-brand-500/20 flex items-center justify-center text-accent-cyan text-sm font-bold flex-shrink-0">
                      {source.owner_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate">
                        {source.owner_name}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span>{source.connection_count} connections</span>
                        <span>·</span>
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(source.uploaded_at)}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(source.id)}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                      title="Remove source"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-dark-glassBorder">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-brand-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-zinc-500 leading-relaxed">
              Each source adds 2nd+ degree paths. Upload friends&apos; CSVs to discover multi-hop referral chains.
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
