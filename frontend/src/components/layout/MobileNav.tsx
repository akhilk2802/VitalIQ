import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/contexts/SidebarContext'
import { useAuth } from '@/contexts/AuthContext'
import { NAV_ITEMS, NAV_ITEMS_SECONDARY, DATA_ENTRY_ITEMS } from '@/lib/constants'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  LayoutDashboard,
  TrendingUp,
  Bell,
  GitBranch,
  Sun,
  Plug,
  Database,
  Settings,
  Plus,
  ChevronDown,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
  LogOut,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'

const iconMap: Record<string, LucideIcon> = {
  LayoutDashboard,
  TrendingUp,
  Bell,
  GitBranch,
  Sun,
  Plug,
  Database,
  Settings,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
}

export function MobileNav() {
  const { isMobileOpen, closeMobile } = useSidebar()
  const { user, logout } = useAuth()
  const location = useLocation()
  const [dataEntryOpen, setDataEntryOpen] = useState(false)

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const handleNavClick = () => {
    closeMobile()
  }

  const handleLogout = () => {
    closeMobile()
    logout()
  }

  return (
    <Sheet open={isMobileOpen} onOpenChange={closeMobile}>
      <SheetContent side="left" className="w-[280px] p-0">
        <SheetHeader className="flex h-16 flex-row items-center justify-between border-b px-4">
          <SheetTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <HeartPulse className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold">VitalIQ</span>
          </SheetTitle>
        </SheetHeader>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {/* Main nav items */}
          {NAV_ITEMS.map((item) => {
            const Icon = iconMap[item.icon]
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={handleNavClick}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive(item.path)
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            )
          })}

          <Separator className="my-4" />

          {/* Data Entry Collapsible */}
          <Collapsible open={dataEntryOpen} onOpenChange={setDataEntryOpen}>
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
                <Plus className="h-5 w-5 shrink-0" />
                <span className="flex-1 text-left">Add Data</span>
                <ChevronDown
                  className={cn(
                    'h-4 w-4 transition-transform',
                    dataEntryOpen && 'rotate-180'
                  )}
                />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1 pt-1">
              {DATA_ENTRY_ITEMS.map((item) => {
                const Icon = iconMap[item.icon]
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={handleNavClick}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 pl-10 text-sm font-medium transition-colors',
                      isActive(item.path)
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </CollapsibleContent>
          </Collapsible>

          <Separator className="my-4" />

          {/* Secondary nav items */}
          {NAV_ITEMS_SECONDARY.map((item) => {
            const Icon = iconMap[item.icon]
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={handleNavClick}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive(item.path)
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* User profile section */}
        <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-background p-3">
          <div className="flex items-center gap-3 rounded-lg p-2">
            <Avatar className="h-9 w-9">
              <AvatarImage src={user?.avatar_url} alt={user?.name || user?.email} />
              <AvatarFallback>
                {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium">
                {user?.name || user?.email?.split('@')[0]}
              </p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              className="h-8 w-8 shrink-0"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
