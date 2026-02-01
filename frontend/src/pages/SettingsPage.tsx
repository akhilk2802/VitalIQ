import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Settings, Bell, Shield, Database, Download, Trash2 } from 'lucide-react'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your app preferences and account settings
        </p>
      </div>

      {/* Notifications */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="h-5 w-5 text-muted-foreground" />
          <h2 className="font-medium">Notifications</h2>
        </div>
        
        <div className="space-y-4">
          <SettingItem
            title="Anomaly Alerts"
            description="Get notified when unusual patterns are detected"
            defaultChecked={true}
          />
          <SettingItem
            title="Daily Briefing"
            description="Receive your morning health briefing at 7:00 AM"
            defaultChecked={true}
          />
          <SettingItem
            title="Weekly Summary"
            description="Get a weekly digest of your health trends"
            defaultChecked={false}
          />
        </div>
      </GlassCard>

      {/* Privacy */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-muted-foreground" />
          <h2 className="font-medium">Privacy</h2>
        </div>
        
        <div className="space-y-4">
          <SettingItem
            title="Share Anonymous Data"
            description="Help improve VitalIQ by sharing anonymized usage data"
            defaultChecked={false}
          />
          <SettingItem
            title="AI Analysis"
            description="Allow AI to analyze your health patterns for insights"
            defaultChecked={true}
          />
        </div>
      </GlassCard>

      {/* Data */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-muted-foreground" />
          <h2 className="font-medium">Data Management</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Export Data</p>
              <p className="text-sm text-muted-foreground">
                Download all your health data as CSV or PDF
              </p>
            </div>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
          
          <Separator />
          
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-destructive">Delete Account</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete your account and all data
              </p>
            </div>
            <Button variant="destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </div>
      </GlassCard>

      {/* About */}
      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="h-5 w-5 text-muted-foreground" />
          <h2 className="font-medium">About</h2>
        </div>
        
        <div className="space-y-2 text-sm">
          <p><span className="text-muted-foreground">Version:</span> 1.0.0</p>
          <p><span className="text-muted-foreground">Build:</span> 2026.02.01</p>
        </div>
      </GlassCard>
    </div>
  )
}

function SettingItem({
  title,
  description,
  defaultChecked = false,
}: {
  title: string
  description: string
  defaultChecked?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <label className="relative inline-flex cursor-pointer items-center">
        <input
          type="checkbox"
          defaultChecked={defaultChecked}
          className="peer sr-only"
        />
        <div className="peer h-6 w-11 rounded-full bg-muted after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-muted-foreground after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:bg-primary-foreground"></div>
      </label>
    </div>
  )
}
