import { useAuth } from '@/contexts/AuthContext'
import { useSidebar } from '@/contexts/SidebarContext'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Menu, Search, Bell, User, Settings, LogOut, AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { anomaliesApi } from '@/api'

interface HeaderProps {
  onOpenCommandPalette?: () => void
}

export function Header({ onOpenCommandPalette }: HeaderProps) {
  const { user, logout } = useAuth()
  const { toggleMobile, isCollapsed } = useSidebar()

  // Fetch recent anomalies for notification badge
  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', 'recent', 5],
    queryFn: () => anomaliesApi.getRecentAnomalies(5),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const unacknowledgedCount = anomalies?.filter((a) => !a.is_acknowledged).length || 0

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur-xl lg:px-6">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={toggleMobile}
      >
        <Menu className="h-5 w-5" />
        <span className="sr-only">Toggle menu</span>
      </Button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Command palette trigger */}
      <Button
        variant="outline"
        size="sm"
        className="hidden gap-2 text-muted-foreground md:flex"
        onClick={onOpenCommandPalette}
      >
        <Search className="h-4 w-4" />
        <span>Search...</span>
        <kbd className="pointer-events-none ml-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-xs font-medium opacity-100 sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </Button>

      {/* Search icon button (mobile) */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onOpenCommandPalette}
      >
        <Search className="h-5 w-5" />
      </Button>

      {/* Notifications */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            {/* Notification badge - only show if there are unacknowledged anomalies */}
            {unacknowledgedCount > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
                {unacknowledgedCount > 9 ? '9+' : unacknowledgedCount}
              </span>
            )}
            <span className="sr-only">Notifications</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="end">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Notifications</h4>
              <Link
                to="/alerts"
                className="text-xs text-primary hover:underline"
              >
                View all
              </Link>
            </div>
            {anomalies && anomalies.length > 0 ? (
              <div className="space-y-2">
                {anomalies.slice(0, 3).map((anomaly) => (
                  <Link
                    key={anomaly.id}
                    to="/alerts"
                    className="flex items-start gap-3 rounded-lg p-2 hover:bg-muted transition-colors"
                  >
                    <AlertTriangle
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        anomaly.severity === 'high'
                          ? 'text-destructive'
                          : anomaly.severity === 'medium'
                          ? 'text-yellow-500'
                          : 'text-muted-foreground'
                      }`}
                    />
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {anomaly.metric_name.replace(/_/g, ' ')}
                      </p>
                      <p className="text-xs text-muted-foreground line-clamp-1">
                        {anomaly.explanation || `Unusual ${anomaly.metric_name} detected`}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center">
                <Bell className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">
                  No new notifications
                </p>
              </div>
            )}
          </div>
        </PopoverContent>
      </Popover>

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative h-9 w-9 rounded-full">
            <Avatar className="h-9 w-9">
              <AvatarImage src={user?.avatar_url} alt={user?.name || user?.email} />
              <AvatarFallback>
                {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">
                {user?.name || user?.email?.split('@')[0]}
              </p>
              <p className="text-xs leading-none text-muted-foreground">
                {user?.email}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link to="/profile" className="cursor-pointer">
              <User className="mr-2 h-4 w-4" />
              Profile
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link to="/settings" className="cursor-pointer">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={logout} className="cursor-pointer text-destructive">
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
