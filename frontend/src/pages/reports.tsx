
import { BarChart3 } from "lucide-react"
import { PagePlaceholder } from "@/components/layout/page-placeholder"

export function Reports() {
  return (
    <PagePlaceholder
      title="Reports"
      description="Monitor ticket trends, support performance and IT operations."
      icon={<BarChart3 className="size-6" />}
    />
  )
}
