
import { BookOpen } from "lucide-react"
import { PagePlaceholder } from "@/components/layout/page-placeholder"

export function KnowledgeBase() {
  return (
    <PagePlaceholder
      title="Knowledge Base"
      description="Access and manage IT guides, troubleshooting articles and solutions."
      icon={<BookOpen className="size-6" />}
    />
  )
}
