import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/contexts/SidebarContext'
import { useAuth } from '@/contexts/AuthContext'
import { useSettings } from '@/contexts/SettingsContext'
import { NAV_ITEMS, NAV_ITEMS_SECONDARY, DATA_ENTRY_ITEMS, MOCK_DATA_NAV_ITEM } from '@/lib/constants'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
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
  ChevronLeft,
  ChevronRight,
  Plus,
  ChevronDown,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
  LogOut,
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

export function Sidebar() {
  const { isCollapsed, toggleCollapsed } = useSidebar()
  const { user, logout } = useAuth()
  const { settings } = useSettings()
  const location = useLocation()
  const [dataEntryOpen, setDataEntryOpen] = useState(false)

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border bg-card/50 backdrop-blur-xl transition-all duration-300',
        isCollapsed ? 'w-[70px]' : 'w-[240px]'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4">
        {!isCollapsed && (
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <HeartPulse className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-semibold">VitalIQ</span>
          </Link>
        )}
        {isCollapsed && (
          <div className="flex w-full justify-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <HeartPulse className="h-5 w-5 text-primary-foreground" />
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {/* Main nav items */}
        {NAV_ITEMS.map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive(item.path)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                isCollapsed && 'justify-center px-2'
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          )
        })}

        <Separator className="my-4" />

        {/* Data Entry Collapsible */}
        <Collapsible open={dataEntryOpen && !isCollapsed} onOpenChange={setDataEntryOpen}>
          <CollapsibleTrigger asChild>
            <button
              className={cn(
                'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
                isCollapsed && 'justify-center px-2'
              )}
              title={isCollapsed ? 'Add Data' : undefined}
            >
              <Plus className="h-5 w-5 shrink-0" />
              {!isCollapsed && (
                <>
                  <span className="flex-1 text-left">Add Data</span>
                  <ChevronDown
                    className={cn(
                      'h-4 w-4 transition-transform',
                      dataEntryOpen && 'rotate-180'
                    )}
                  />
                </>
              )}
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-1 pt-1">
            {DATA_ENTRY_ITEMS.map((item) => {
              const Icon = iconMap[item.icon]
              return (
                <Link
                  key={item.path}
                  to={item.path}
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
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive(item.path)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                isCollapsed && 'justify-center px-2'
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          )
        })}

        {/* Mock Data - only shown when enabled in settings */}
        {settings.mockDataEnabled && (
          <>
            {(() => {
              const Icon = iconMap[MOCK_DATA_NAV_ITEM.icon]
              return (
                <Link
                  to={MOCK_DATA_NAV_ITEM.path}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive(MOCK_DATA_NAV_ITEM.path)
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                    isCollapsed && 'justify-center px-2'
                  )}
                  title={isCollapsed ? MOCK_DATA_NAV_ITEM.label : undefined}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!isCollapsed && <span>{MOCK_DATA_NAV_ITEM.label}</span>}
                </Link>
              )
            })()}
          </>
        )}
      </nav>

      {/* User profile section */}
      <div className="border-t border-border p-3">
        <div
          className={cn(
            'flex items-center gap-3 rounded-lg p-2',
            isCollapsed && 'justify-center'
          )}
        >
          <Avatar className="h-9 w-9">
            <AvatarImage src={user?.avatar_url} alt={user?.name || user?.email} />
            <AvatarFallback>
              {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
            </AvatarFallback>
          </Avatar>
          {!isCollapsed && (
            <div className="flex-1 truncate">
              <p className="truncate text-sm font-medium">
                {user?.name || user?.email?.split('@')[0]}
              </p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
          )}
          {!isCollapsed && (
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="h-8 w-8 shrink-0"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleCollapsed}
        className="absolute -right-3 top-20 h-6 w-6 rounded-full border bg-background shadow-md"
      >
        {isCollapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </Button>
    </aside>
  )
}
