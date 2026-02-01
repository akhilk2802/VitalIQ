import { Outlet } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useSidebar, SidebarProvider } from '@/contexts/SidebarContext'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { MobileNav } from './MobileNav'
import { ChatDrawer, ChatFAB } from '@/components/chat'
import { CommandPalette } from '@/components/command'
import { useState } from 'react'

function AppLayoutContent() {
  const { isCollapsed } = useSidebar()
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  const openCommandPalette = () => {
    setCommandPaletteOpen(true)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile Navigation */}
      <MobileNav />

      {/* Main content */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          isCollapsed ? 'lg:pl-[70px]' : 'lg:pl-[240px]'
        )}
      >
        <Header onOpenCommandPalette={openCommandPalette} />
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Chat FAB & Drawer */}
      <ChatFAB onClick={() => setChatOpen(true)} />
      <ChatDrawer open={chatOpen} onOpenChange={setChatOpen} />

      {/* Command Palette */}
      <CommandPalette open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen} />
    </div>
  )
}

export function AppLayout() {
  return (
    <SidebarProvider>
      <AppLayoutContent />
    </SidebarProvider>
  )
}
