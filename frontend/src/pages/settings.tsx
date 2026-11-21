
import { Settings } from "lucide-react"
import { PagePlaceholder } from "@/components/layout/page-placeholder"

export function SettingsPage() {
  return (
    <PagePlaceholder
      title="Settings"
      description="Configure application preferences, security and organisation settings."
      icon={<Settings className="size-6" />}
    />
  )
}
