
import { Users } from "lucide-react"
import { PagePlaceholder } from "@/components/layout/page-placeholder"

export function UsersPage() {
  return (
    <PagePlaceholder
      title="Users"
      description="Manage employees, IT support agents and organisation access."
      icon={<Users className="size-6" />}
    />
  )
}
