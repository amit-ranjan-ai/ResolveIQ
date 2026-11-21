
import { LoaderCircle } from "lucide-react"

interface PageLoaderProps {
  message?: string
}

export function PageLoader({
  message = "Loading, please wait...",
}: PageLoaderProps) {
  return (
    <div
      className="flex min-h-[300px] flex-col items-center justify-center gap-4"
      role="status"
      aria-live="polite"
    >
      <div className="flex size-14 items-center justify-center rounded-full bg-primary/10">
        <LoaderCircle className="size-7 animate-spin text-primary" />
      </div>

      <div className="text-center">
        <p className="text-sm font-semibold">{message}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          This should only take a moment.
        </p>
      </div>
    </div>
  )
}
