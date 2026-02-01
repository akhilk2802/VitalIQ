import { useAuth } from '@/contexts/AuthContext'
import { formatDateFull } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { User, Mail, Calendar, Edit } from 'lucide-react'

export function ProfilePage() {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">
          Manage your personal information
        </p>
      </div>

      {/* Profile Card */}
      <GlassCard className="p-8">
        <div className="flex flex-col items-center sm:flex-row sm:items-start gap-6">
          <div className="relative">
            <Avatar className="h-24 w-24">
              <AvatarImage src={user?.avatar_url} alt={user?.name || user?.email} />
              <AvatarFallback className="text-2xl">
                {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </AvatarFallback>
            </Avatar>
            <Button
              size="icon"
              variant="secondary"
              className="absolute -bottom-1 -right-1 h-8 w-8 rounded-full"
            >
              <Edit className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-xl font-semibold">
              {user?.name || user?.email?.split('@')[0]}
            </h2>
            <p className="text-muted-foreground">{user?.email}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Member since {formatDateFull(user?.created_at || new Date())}
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Edit Profile */}
      <GlassCard className="p-6">
        <h2 className="font-medium mb-6">Personal Information</h2>
        
        <form className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="name"
                  defaultValue={user?.name || ''}
                  placeholder="Enter your name"
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  defaultValue={user?.email || ''}
                  disabled
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          <div className="pt-4">
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </GlassCard>

      {/* Stats */}
      <GlassCard className="p-6">
        <h2 className="font-medium mb-4">Your Stats</h2>
        
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-muted p-4 text-center">
            <p className="text-3xl font-bold text-sleep">150</p>
            <p className="text-sm text-muted-foreground">Days Tracked</p>
          </div>
          <div className="rounded-lg bg-muted p-4 text-center">
            <p className="text-3xl font-bold text-exercise">423</p>
            <p className="text-sm text-muted-foreground">Workouts Logged</p>
          </div>
          <div className="rounded-lg bg-muted p-4 text-center">
            <p className="text-3xl font-bold text-nutrition">1,247</p>
            <p className="text-sm text-muted-foreground">Meals Recorded</p>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
