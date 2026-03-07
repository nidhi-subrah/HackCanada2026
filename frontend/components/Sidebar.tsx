"use client"
import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Waypoints, Home, Users, Upload, Search, Settings, LogOut, UserPlus } from "lucide-react"
import { useAuth } from "./AuthContext"
import ConnectionsPanel from "./ConnectionsPanel"

const navItems = [
  { icon: Home, href: "/dashboard", label: "Dashboard" },
  { icon: Users, href: "/connections", label: "Connections" },
  { icon: Upload, href: "/upload", label: "Upload" },
  { icon: Search, href: "/search", label: "Search" },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const [panelOpen, setPanelOpen] = useState(false)

  return (
    <>
      <aside className="w-20 bg-dark-surface border-r border-dark-glassBorder flex flex-col items-center py-6 gap-2 z-50 relative">
        <Link href="/" className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center mb-8 shadow-glow">
          <Waypoints className="w-6 h-6 text-white" />
        </Link>

        <nav className="flex-1 flex flex-col gap-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href === "/search" && pathname.startsWith("/search"))
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
                  isActive 
                    ? "bg-brand-500/20 text-brand-400" 
                    : "text-zinc-500 hover:text-white hover:bg-dark-elevated"
                }`}
                title={item.label}
              >
                <item.icon className="w-5 h-5" />
              </Link>
            )
          })}

          {/* Add Connections button */}
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${
              panelOpen
                ? "bg-accent-cyan/20 text-accent-cyan"
                : "text-zinc-500 hover:text-white hover:bg-dark-elevated"
            }`}
            title="Add Connections"
          >
            <UserPlus className="w-5 h-5" />
          </button>
        </nav>

        <div className="flex flex-col gap-2 mt-auto">
          <button 
            onClick={logout}
            className="w-12 h-12 rounded-xl flex items-center justify-center text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
          <button className="w-12 h-12 rounded-xl flex items-center justify-center text-zinc-500 hover:text-white hover:bg-dark-elevated transition-all" title="Settings">
            <Settings className="w-5 h-5" />
          </button>
          <div className="w-10 h-10 rounded-full overflow-hidden border border-dark-glassBorder bg-gradient-to-br from-accent-amber to-accent-rose">
            {user?.picture ? (
              <img src={user.picture} alt={user.name || "User"} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white text-xs font-bold">
                {(user?.name || "U").charAt(0).toUpperCase()}
              </div>
            )}
          </div>
        </div>
      </aside>

      <ConnectionsPanel isOpen={panelOpen} onClose={() => setPanelOpen(false)} />
    </>
  )
}
