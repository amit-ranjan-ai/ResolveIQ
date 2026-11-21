
import { AlertCircle, RefreshCw } from "lucide-react"

interface PageErrorProps {
  message?: string
  onRetry?: () => void
}

export function PageError({
  message = "Something went wrong while loading this page.",
  onRetry,
}: PageErrorProps) {
  return (
    <div
      className="flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-xl border bg-card p-6 text-center"
      role="alert"
    >
      <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertCircle className="size-7" />
      </div>

      <div className="max-w-md">
        <h2 className="text-lg font-semibold">Unable to load content</h2>
        <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      </div>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <RefreshCw className="size-4" />
          Try again
        </button>
      )}
    </div>
  )
}
