"use client"
import React, { useRef, useCallback, useMemo, useEffect } from "react"
import dynamic from "next/dynamic"
import * as THREE from "three"

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), { ssr: false })

type GraphNode = {
  id: string
  name: string
  type: "user" | "person" | "company"
  initials?: string
  is_recruiter?: boolean
  logo?: string
}

type GraphLink = {
  source: string
  target: string
  label: string
}

type GraphData = {
  nodes: GraphNode[]
  links: GraphLink[]
}

const NODE_COLORS: Record<string, string> = {
  user: "#8B5CF6",
  person: "#06B6D4",
  company: "#F59E0B",
}

const DEMO_COMPANIES = [
  { name: "Google", logo: "https://logo.clearbit.com/google.com" },
  { name: "Meta", logo: "https://logo.clearbit.com/meta.com" },
  { name: "Apple", logo: "https://logo.clearbit.com/apple.com" },
  { name: "Amazon", logo: "https://logo.clearbit.com/amazon.com" },
  { name: "Microsoft", logo: "https://logo.clearbit.com/microsoft.com" },
  { name: "Netflix", logo: "https://logo.clearbit.com/netflix.com" },
  { name: "Spotify", logo: "https://logo.clearbit.com/spotify.com" },
  { name: "Stripe", logo: "https://logo.clearbit.com/stripe.com" },
  { name: "Shopify", logo: "https://logo.clearbit.com/shopify.com" },
  { name: "Notion", logo: "https://logo.clearbit.com/notion.so" },
  { name: "Figma", logo: "https://logo.clearbit.com/figma.com" },
  { name: "Vercel", logo: "https://logo.clearbit.com/vercel.com" },
  { name: "OpenAI", logo: "https://logo.clearbit.com/openai.com" },
  { name: "Anthropic", logo: "https://logo.clearbit.com/anthropic.com" },
  { name: "Tesla", logo: "https://logo.clearbit.com/tesla.com" },
]

const DEMO_NAMES = [
  "Alex Chen", "Sarah Kim", "James Wilson", "Emily Zhang", "Michael Brown",
  "Jessica Lee", "David Park", "Amanda Liu", "Chris Taylor", "Nicole Wang",
  "Ryan Martinez", "Olivia Johnson", "Kevin Wu", "Rachel Green", "Daniel Smith",
  "Sophia Anderson", "Justin Huang", "Ashley Moore", "Brandon Lin", "Megan Davis",
]

function getInitials(name: string): string {
  return name.split(" ").map(n => n[0]).join("").toUpperCase()
}

function generateDemoData(): GraphData {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []
  
  nodes.push({
    id: "user",
    name: "You",
    type: "user",
    initials: "ME",
  })
  
  DEMO_COMPANIES.forEach((company, i) => {
    nodes.push({
      id: `company-${i}`,
      name: company.name,
      type: "company",
      initials: company.name.substring(0, 2).toUpperCase(),
      logo: company.logo,
    })
  })
  
  DEMO_NAMES.forEach((name, i) => {
    const isRecruiter = i % 5 === 0
    nodes.push({
      id: `person-${i}`,
      name: name,
      type: "person",
      initials: getInitials(name),
      is_recruiter: isRecruiter,
    })
    
    links.push({
      source: "user",
      target: `person-${i}`,
      label: "KNOWS",
    })
    
    const companyIdx = i % DEMO_COMPANIES.length
    links.push({
      source: `person-${i}`,
      target: `company-${companyIdx}`,
      label: "WORKS_AT",
    })
  })
  
  return { nodes, links }
}

function createNodeSprite(
  text: string,
  bgColor: string,
  name: string,
  isRecruiter: boolean = false
): THREE.Sprite {
  const canvas = document.createElement("canvas")
  const size = 128
  canvas.width = size * 2
  canvas.height = size * 2.5
  const ctx = canvas.getContext("2d")!
  
  const centerX = size
  const centerY = size * 0.8
  const radius = size * 0.5
  
  if (isRecruiter) {
    ctx.beginPath()
    ctx.arc(centerX, centerY, radius + 8, 0, Math.PI * 2)
    ctx.strokeStyle = "#10B981"
    ctx.lineWidth = 6
    ctx.stroke()
  }
  
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
  ctx.fillStyle = bgColor
  ctx.fill()
  
  ctx.font = `bold ${size * 0.4}px Arial, sans-serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.fillStyle = "#FFFFFF"
  ctx.fillText(text, centerX, centerY)
  
  ctx.font = `${size * 0.2}px Arial, sans-serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "top"
  ctx.fillStyle = "#E4E4E7"
  ctx.fillText(name, centerX, centerY + radius + 12)
  
  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(20, 25, 1)
  
  return sprite
}

function createCompanySprite(
  logoUrl: string,
  name: string,
  fallbackText: string
): THREE.Sprite {
  const canvas = document.createElement("canvas")
  const size = 128
  canvas.width = size * 2
  canvas.height = size * 2.5
  const ctx = canvas.getContext("2d")!
  
  const centerX = size
  const centerY = size * 0.8
  const radius = size * 0.5
  
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius + 4, 0, Math.PI * 2)
  ctx.strokeStyle = "#F59E0B"
  ctx.lineWidth = 4
  ctx.stroke()
  
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
  ctx.fillStyle = "#1f1f2e"
  ctx.fill()
  
  ctx.font = `bold ${size * 0.35}px Arial, sans-serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.fillStyle = "#F59E0B"
  ctx.fillText(fallbackText, centerX, centerY)
  
  ctx.font = `${size * 0.18}px Arial, sans-serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "top"
  ctx.fillStyle = "#FCD34D"
  ctx.fillText(name, centerX, centerY + radius + 12)
  
  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(20, 25, 1)
  
  return sprite
}

type Props = {
  width?: number
  height?: number
}

export default function DemoGraph3D({ width, height }: Props) {
  const graphRef = useRef<any>(null)
  const angle = useRef(0)
  
  const demoData = useMemo(() => generateDemoData(), [])

  useEffect(() => {
    const interval = setInterval(() => {
      if (graphRef.current) {
        angle.current += 0.003
        const distance = 350
        const x = distance * Math.sin(angle.current)
        const z = distance * Math.cos(angle.current)
        graphRef.current.cameraPosition({ x, y: 100, z })
      }
    }, 16)
    
    return () => clearInterval(interval)
  }, [])
  
  const create3DNode = useCallback((node: any) => {
    const color = NODE_COLORS[node.type as string] || "#888"
    const group = new THREE.Group()
    
    if (node.type === "company") {
      const sprite = createCompanySprite(
        node.logo || "",
        node.name,
        node.initials || node.name.substring(0, 2).toUpperCase()
      )
      group.add(sprite)
    } else {
      const initials = node.initials || getInitials(node.name)
      const sprite = createNodeSprite(initials, color, node.name, node.is_recruiter)
      group.add(sprite)
      
      if (node.type === "user") {
        const glowGeometry = new THREE.SphereGeometry(12, 16, 16)
        const glowMaterial = new THREE.MeshBasicMaterial({
          color: "#8B5CF6",
          transparent: true,
          opacity: 0.25,
        })
        const glow = new THREE.Mesh(glowGeometry, glowMaterial)
        group.add(glow)
      }
    }
    
    return group
  }, [])

  return (
    <div style={{ width: width || "100%", height: height || "100%" }}>
      <ForceGraph3D
        ref={graphRef}
        graphData={demoData}
        width={width}
        height={height}
        backgroundColor="#0a0a12"
        nodeThreeObject={create3DNode}
        nodeLabel={() => ""}
        linkColor={(link: any) => link.label === "KNOWS" ? "rgba(139,92,246,0.4)" : "rgba(245,158,11,0.4)"}
        linkWidth={1.5}
        linkOpacity={0.5}
        cooldownTicks={100}
        enableNodeDrag={false}
        enableNavigationControls={false}
        showNavInfo={false}
      />
    </div>
  )
}
