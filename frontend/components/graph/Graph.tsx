"use client"
import React, { useEffect, useRef, useState, useCallback, useMemo } from "react"
import axios from "axios"
import dynamic from "next/dynamic"

// @ts-ignore - dynamic import without types
const ForceGraph2D = dynamic(() => import("react-force-graph-2d").then(mod => mod.default || mod), { ssr: false })

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

type GraphNode = {
  id: string
  name: string
  type: "user" | "person" | "company" | "source_owner"
  title?: string
  is_recruiter?: boolean
  group?: string
  x?: number
  y?: number
}

type GraphLink = {
  source: string | GraphNode
  target: string | GraphNode
  label: string
  source_id?: string
}

type GroupInfo = {
  id: string
  name: string
  color: string
}

type GraphData = {
  nodes: GraphNode[]
  links: GraphLink[]
  groups?: GroupInfo[]
}

type Props = {
  width?: number
  height?: number
}

const NODE_SIZES: Record<string, number> = {
  user: 10,
  person: 5,
  company: 7,
  source_owner: 8,
}

// Fallback colors if no group info
const FALLBACK_COLORS: Record<string, string> = {
  user: "#8B5CF6",
  person: "#06B6D4",
  company: "#F59E0B",
  source_owner: "#34d399",
}

export default function Graph({ width, height }: Props) {
  const fgRef = useRef<any>(null)
  const [data, setData] = useState<GraphData>({ nodes: [], links: [], groups: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Build a group -> color lookup from the groups metadata
  const groupColorMap = useMemo(() => {
    const map: Record<string, string> = {}
    if (data.groups) {
      for (const g of data.groups) {
        map[g.id] = g.color
      }
    }
    return map
  }, [data.groups])

  const getNodeColor = useCallback((node: GraphNode) => {
    if (node.type === "user") return "#8B5CF6"
    if (node.type === "company") return "#F59E0B"
    // Use group color for person / source_owner nodes
    if (node.group && groupColorMap[node.group]) {
      return groupColorMap[node.group]
    }
    return FALLBACK_COLORS[node.type] || "#888"
  }, [groupColorMap])

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      setError(null)
      const userId = localStorage.getItem("user_id")
      if (!userId) {
        setError("No user found. Please upload your CSV first.")
        setLoading(false)
        return
      }
      try {
        const res = await axios.get(`${API_URL}/api/graph/overview`, {
          params: { user_id: userId },
        })
        if (!mounted) return
        setData(res.data)
      } catch (err: any) {
        if (!mounted) return
        setError(err?.message ?? "Failed to load graph")
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  // Apply clustering force: nudge nodes in the same group toward each other
  useEffect(() => {
    if (!fgRef.current || !data.groups || data.groups.length <= 1) return

    const fg = fgRef.current
    // Compute group centers and apply a gentle clustering force
    const groupCenters: Record<string, { x: number, y: number }> = {}
    const groups = data.groups || []
    const angleStep = (2 * Math.PI) / Math.max(groups.length, 1)
    const clusterRadius = 200

    groups.forEach((g, i) => {
      groupCenters[g.id] = {
        x: Math.cos(angleStep * i) * clusterRadius,
        y: Math.sin(angleStep * i) * clusterRadius,
      }
    })

    fg.d3Force("cluster", (alpha: number) => {
      const nodes = fg.graphData().nodes
      for (const node of nodes) {
        const center = groupCenters[(node as any).group]
        if (center && node.x != null && node.y != null) {
          const k = alpha * 0.3
          node.vx = (node.vx || 0) + (center.x - node.x) * k
          node.vy = (node.vy || 0) + (center.y - node.y) * k
        }
      }
    })

    fg.d3ReheatSimulation()
  }, [data])

  const handleNodeClick = useCallback((node: any) => {
    if (fgRef.current && node.x !== undefined && node.y !== undefined) {
      fgRef.current.centerAt(node.x, node.y, 600)
      fgRef.current.zoom(2.5, 600)
    }
  }, [])

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const r = NODE_SIZES[node.type] || 5
    const color = getNodeColor(node)

    // Glow for user node
    if (node.type === "user") {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI)
      ctx.fillStyle = "rgba(139, 92, 246, 0.25)"
      ctx.fill()
    }

    // Glow ring for source owners
    if (node.type === "source_owner") {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI)
      ctx.fillStyle = "rgba(52, 211, 153, 0.2)"
      ctx.fill()
    }

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    // Recruiter ring
    if (node.is_recruiter) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI)
      ctx.strokeStyle = "#10B981"
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    // Label
    const fontSize = Math.max(10 / globalScale, 2)
    if (globalScale > 0.6 || node.type === "user" || node.type === "company" || node.type === "source_owner") {
      ctx.font = `${(node.type === "user" || node.type === "source_owner") ? "bold " : ""}${fontSize}px Inter, sans-serif`
      ctx.textAlign = "center"
      ctx.textBaseline = "top"
      ctx.fillStyle = node.type === "company" ? "#FCD34D" : "#E4E4E7"
      ctx.fillText(node.name || "", node.x, node.y + r + 2)
    }
  }, [getNodeColor])

  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const src = link.source
    const tgt = link.target
    if (!src || !tgt || src.x == null || tgt.x == null) return

    ctx.beginPath()
    ctx.moveTo(src.x, src.y)
    ctx.lineTo(tgt.x, tgt.y)
    ctx.strokeStyle = link.label === "KNOWS" ? "rgba(139,92,246,0.3)" : "rgba(245,158,11,0.3)"
    ctx.lineWidth = link.label === "KNOWS" ? 0.8 : 0.5
    ctx.stroke()

    // Edge label when zoomed in
    if (globalScale > 1.5) {
      const mx = (src.x + tgt.x) / 2
      const my = (src.y + tgt.y) / 2
      const fontSize = Math.max(8 / globalScale, 2)
      ctx.font = `${fontSize}px Inter, sans-serif`
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      ctx.fillStyle = "rgba(161,161,170,0.7)"
      ctx.fillText(link.label === "KNOWS" ? "knows" : "works at", mx, my)
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Building your network graph...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-accent-rose">{error}</p>
      </div>
    )
  }

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={data}
      width={width}
      height={height}
      backgroundColor="rgba(0,0,0,0)"
      nodeCanvasObject={paintNode}
      nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
        const r = NODE_SIZES[node.type as string] || 5
        ctx.beginPath()
        ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI)
        ctx.fillStyle = color
        ctx.fill()
      }}
      linkCanvasObject={paintLink}
      linkDirectionalArrowLength={4}
      linkDirectionalArrowRelPos={0.9}
      onNodeClick={handleNodeClick}
      cooldownTicks={150}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.3}
    />
  )
}