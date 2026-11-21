
import {
  Ticket,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  ArrowUpRight,
  Sparkles,
} from "lucide-react"

const stats = [
  {
    title: "Total Tickets",
    value: "1,284",
    change: "+12.5%",
    description: "Compared to last month",
    icon: Ticket,
  },
  {
    title: "Open Tickets",
    value: "186",
    change: "-8.2%",
    description: "Compared to last month",
    icon: AlertCircle,
  },
  {
    title: "Resolved Tickets",
    value: "1,098",
    change: "+18.4%",
    description: "Compared to last month",
    icon: CheckCircle2,
  },
  {
    title: "Avg. Resolution Time",
    value: "4.2 hrs",
    change: "-15.3%",
    description: "Compared to last month",
    icon: Clock,
  },
]

const recentTickets = [
  {
    id: "INC-1024",
    title: "Unable to access company VPN",
    category: "Network",
    priority: "High",
    status: "Open",
    requester: "John Smith",
  },
  {
    id: "INC-1023",
    title: "Laptop performance is very slow",
    category: "Hardware",
    priority: "Medium",
    status: "In Progress",
    requester: "Sarah Johnson",
  },
  {
    id: "INC-1022",
    title: "Email synchronization issue",
    category: "Software",
    priority: "Low",
    status: "Resolved",
    requester: "Michael Brown",
  },
  {
    id: "INC-1021",
    title: "Unable to install required software",
    category: "Software",
    priority: "Medium",
    status: "Open",
    requester: "Emily Davis",
  },
]

export function Dashboard() {
  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Dashboard Overview
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor your IT support performance and operations.
          </p>
        </div>

        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Ticket className="size-4" />
          Create Ticket
        </button>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon

          return (
            <div
              key={stat.title}
              className="rounded-xl border bg-card p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </p>
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                  <Icon className="size-4" />
                </div>
              </div>

              <p className="mt-4 text-3xl font-bold tracking-tight">
                {stat.value}
              </p>

              <div className="mt-2 flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1 font-medium text-emerald-600">
                  <TrendingUp className="size-3" />
                  {stat.change}
                </span>
                <span className="text-muted-foreground">
                  {stat.description}
                </span>
              </div>
            </div>
          )
        })}
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <div className="rounded-xl border bg-card p-5 xl:col-span-2">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="font-semibold">Recent Tickets</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Latest IT support requests
              </p>
            </div>

            <button
              type="button"
              className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              View all
              <ArrowUpRight className="size-4" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="pb-3 font-medium">Ticket</th>
                  <th className="pb-3 font-medium">Requester</th>
                  <th className="pb-3 font-medium">Priority</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>

              <tbody>
                {recentTickets.map((ticket) => (
                  <tr key={ticket.id} className="border-b last:border-0">
                    <td className="py-4">
                      <p className="font-medium">{ticket.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {ticket.id} · {ticket.category}
                      </p>
                    </td>

                    <td className="py-4 text-muted-foreground">
                      {ticket.requester}
                    </td>

                    <td className="py-4">
                      <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium">
                        {ticket.priority}
                      </span>
                    </td>

                    <td className="py-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          ticket.status === "Resolved"
                            ? "bg-emerald-500/10 text-emerald-600"
                            : ticket.status === "In Progress"
                              ? "bg-blue-500/10 text-blue-600"
                              : "bg-amber-500/10 text-amber-600"
                        }`}
                      >
                        {ticket.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-primary/10 p-2 text-primary">
              <Sparkles className="size-4" />
            </div>
            <h2 className="font-semibold">AI Operations</h2>
          </div>

          <p className="mt-2 text-sm text-muted-foreground">
            Your AI assistant's activity overview.
          </p>

          <div className="mt-6 space-y-5">
            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  AI Categorization
                </span>
                <span className="font-semibold">92%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full w-[92%] rounded-full bg-primary" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  AI Priority Accuracy
                </span>
                <span className="font-semibold">87%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full w-[87%] rounded-full bg-primary" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  Knowledge Suggestions
                </span>
                <span className="font-semibold">76%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full w-[76%] rounded-full bg-primary" />
              </div>
            </div>
          </div>

          <div className="mt-7 rounded-lg border border-primary/20 bg-primary/5 p-4">
            <p className="text-sm font-semibold">AI Insight</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Network-related tickets are currently the most common category.
              Consider reviewing recurring VPN issues.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
