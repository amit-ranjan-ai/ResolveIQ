
import type { ReactNode } from "react"

interface PagePlaceholderProps {
  title: string
  description: string
  icon: ReactNode
}

export function PagePlaceholder({
  title,
  description,
  icon,
}: PagePlaceholderProps) {
  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {icon}
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border bg-card p-8 text-center shadow-sm">
        <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
          {icon}
        </div>

        <h2 className="mt-4 text-lg font-semibold">
          {title} workspace
        </h2>

        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          This section is being prepared. Its functionality will be added in
          the upcoming development stages.
        </p>
      </section>
    </div>
  )
}
