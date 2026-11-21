
import { useState } from "react"
import {
  Ticket,
  CircleDot,
  Clock,
  CheckCircle2,
  Search,
  Filter,
  Plus,
} from "lucide-react"

import {
  CreateTicketDialog,
  type CreateTicketData,
} from "@/components/layout/create-ticket-dialog"

interface TicketRecord {
  id: string
  subject: string
  description?: string
  category: string
  priority: string
  status: string
  requester: string
  date: string
}

const initialTickets: TicketRecord[] = [
  {
    id: "INC-1024",
    subject: "Unable to access company VPN",
    category: "Network",
    priority: "High",
    status: "Open",
    requester: "John Smith",
    date: "21 Nov 2026",
  },
  {
    id: "INC-1023",
    subject: "Laptop performance is very slow",
    category: "Hardware",
    priority: "Medium",
    status: "In Progress",
    requester: "Sarah Johnson",
    date: "21 Nov 2026",
  },
  {
    id: "INC-1022",
    subject: "Email synchronization issue",
    category: "Software",
    priority: "Low",
    status: "Resolved",
    requester: "Michael Brown",
    date: "20 Nov 2026",
  },
  {
    id: "INC-1021",
    subject: "Unable to install required software",
    category: "Software",
    priority: "Medium",
    status: "Open",
    requester: "Emily Davis",
    date: "20 Nov 2026",
  },
  {
    id: "INC-1020",
    subject: "Printer not responding",
    category: "Hardware",
    priority: "Low",
    status: "Resolved",
    requester: "David Wilson",
    date: "19 Nov 2026",
  },
]

function getStatusStyle(status: string) {
  switch (status) {
    case "Open":
      return "bg-orange-500/10 text-orange-600"
    case "In Progress":
      return "bg-blue-500/10 text-blue-600"
    case "Resolved":
      return "bg-green-500/10 text-green-600"
    default:
      return "bg-muted text-muted-foreground"
  }
}

function getPriorityStyle(priority: string) {
  switch (priority) {
    case "Critical":
      return "text-red-700 font-bold"
    case "High":
      return "text-red-600"
    case "Medium":
      return "text-orange-600"
    case "Low":
      return "text-green-600"
    default:
      return "text-muted-foreground"
  }
}

export function Tickets() {
  const [tickets, setTickets] = useState<TicketRecord[]>(initialTickets)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("All")
  const [dialogOpen, setDialogOpen] = useState(false)

  function handleCreateTicket(data: CreateTicketData) {
    const nextNumber =
      Math.max(
        ...tickets.map((ticket) => Number(ticket.id.replace("INC-", ""))),
        1024,
      ) + 1

    const newTicket: TicketRecord = {
      id: `INC-${nextNumber}`,
      subject: data.subject,
      description: data.description,
      category: data.category,
      priority: data.priority,
      status: "Open",
      requester: data.requester,
      date: new Date().toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    }

    setTickets((previousTickets) => [newTicket, ...previousTickets])
    setDialogOpen(false)
  }

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch = [
      ticket.id,
      ticket.subject,
      ticket.description ?? "",
      ticket.category,
      ticket.requester,
    ]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase())

    const matchesStatus =
      statusFilter === "All" || ticket.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const summaryCards = [
    {
      label: "Total Tickets",
      value: tickets.length,
      icon: Ticket,
      color: "text-primary",
      background: "bg-primary/10",
    },
    {
      label: "Open Tickets",
      value: tickets.filter((ticket) => ticket.status === "Open").length,
      icon: CircleDot,
      color: "text-orange-600",
      background: "bg-orange-500/10",
    },
    {
      label: "In Progress",
      value: tickets.filter((ticket) => ticket.status === "In Progress").length,
      icon: Clock,
      color: "text-blue-600",
      background: "bg-blue-500/10",
    },
    {
      label: "Resolved",
      value: tickets.filter((ticket) => ticket.status === "Resolved").length,
      icon: CheckCircle2,
      color: "text-green-600",
      background: "bg-green-500/10",
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Ticket Management
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track and manage internal IT support requests.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <Plus className="size-4" />
          Create Ticket
        </button>
      </div>

      <div className="rounded-lg border border-dashed px-4 py-3 text-xs text-muted-foreground">
        Sample tickets and newly created tickets are stored in frontend memory
        only. They will not survive a page refresh until backend integration.
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => {
          const Icon = card.icon

          return (
            <div
              key={card.label}
              className="rounded-xl border bg-card p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">
                  {card.label}
                </p>

                <div
                  className={`flex size-10 items-center justify-center rounded-lg ${card.background} ${card.color}`}
                >
                  <Icon className="size-5" />
                </div>
              </div>

              <p className="mt-4 text-3xl font-bold tracking-tight">
                {card.value}
              </p>
            </div>
          )
        })}
      </div>

      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b p-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <h2 className="font-semibold">All Tickets</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Browse and filter support requests.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="flex items-center gap-2 rounded-lg border px-3">
                <Search className="size-4 shrink-0 text-muted-foreground" />

                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search tickets..."
                  aria-label="Search tickets"
                  className="h-10 min-w-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground sm:w-52"
                />
              </div>

              <div className="flex items-center gap-2 rounded-lg border px-3">
                <Filter className="size-4 shrink-0 text-muted-foreground" />

                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  aria-label="Filter tickets by status"
                  className="h-10 min-w-0 bg-transparent text-sm outline-none"
                >
                  <option value="All">All statuses</option>
                  <option value="Open">Open</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Resolved">Resolved</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-5 py-4 font-medium">Ticket</th>
                <th className="px-5 py-4 font-medium">Requester</th>
                <th className="px-5 py-4 font-medium">Category</th>
                <th className="px-5 py-4 font-medium">Priority</th>
                <th className="px-5 py-4 font-medium">Status</th>
                <th className="px-5 py-4 font-medium">Created</th>
              </tr>
            </thead>

            <tbody className="divide-y">
              {filteredTickets.map((ticket) => (
                <tr
                  key={ticket.id}
                  className="transition-colors hover:bg-muted/30"
                >
                  <td className="px-5 py-4">
                    <p className="font-semibold">{ticket.id}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {ticket.subject}
                    </p>
                  </td>

                  <td className="px-5 py-4 font-medium">
                    {ticket.requester}
                  </td>

                  <td className="px-5 py-4 text-muted-foreground">
                    {ticket.category}
                  </td>

                  <td className="px-5 py-4">
                    <span
                      className={`font-semibold ${getPriorityStyle(ticket.priority)}`}
                    >
                      {ticket.priority}
                    </span>
                  </td>

                  <td className="px-5 py-4">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusStyle(ticket.status)}`}
                    >
                      {ticket.status}
                    </span>
                  </td>

                  <td className="px-5 py-4 text-muted-foreground">
                    {ticket.date}
                  </td>
                </tr>
              ))}

              {filteredTickets.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-12 text-center text-muted-foreground"
                  >
                    No tickets found. Try another search or status filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="border-t px-5 py-4 text-xs text-muted-foreground">
          Showing {filteredTickets.length} of {tickets.length} tickets
        </div>
      </section>

      <CreateTicketDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreate={handleCreateTicket}
      />
    </div>
  )
}


