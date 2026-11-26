import { useEffect, useState } from "react";
import {
  Ticket,
  CircleDot,
  Clock,
  CheckCircle2,
  Search,
  Filter,
  Plus,
  X,
  Eye,
  History,
  Activity,
  RefreshCw,
} from "lucide-react";

import {
  CreateTicketDialog,
  type CreateTicketData,
} from "@/components/layout/create-ticket-dialog";

import { useOrganisation } from "@/contexts/organisation-context";
import {
  getOrganisationTickets,
  createOrganisationTicket,
  updateTicket,
  type OrganisationTicket,
} from "@/services/tickets";
import { getMyOrganisationMembership } from "@/services/organisation-memberships";
import {
  getTicketActivities,
  type TicketActivity,
} from "@/services/ticket-activities";

function getPriorityLabel(priority: string) {
  const labels: Record<string, string> = {
    P1: "Critical",
    P2: "High",
    P3: "Medium",
    P4: "Low",
  };

  return labels[priority] ?? priority;
}

function getPriorityStyle(priority: string) {
  switch (priority) {
    case "P1":
      return "text-red-700 font-bold";
    case "P2":
      return "text-red-600";
    case "P3":
      return "text-orange-600";
    case "P4":
      return "text-green-600";
    default:
      return "text-muted-foreground";
  }
}

function getStatusStyle(status: string) {
  switch (status) {
    case "Open":
      return "bg-orange-500/10 text-orange-600";
    case "Assigned":
    case "In Progress":
      return "bg-blue-500/10 text-blue-600";
    case "Pending":
      return "bg-yellow-500/10 text-yellow-700";
    case "Resolved":
      return "bg-green-500/10 text-green-600";
    case "Closed":
      return "bg-muted text-muted-foreground";
    case "Reopened":
      return "bg-purple-500/10 text-purple-600";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(date: string) {
  return new Date(date).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const availableStatuses = [
  "Open",
  "Assigned",
  "In Progress",
  "Pending",
  "Resolved",
  "Closed",
  "Reopened",
];

export function Tickets() {
  const { selectedOrganisationId } = useOrganisation();

  const [tickets, setTickets] = useState<OrganisationTicket[]>([]);
  const [membershipId, setMembershipId] = useState("");
  const [activities, setActivities] = useState<TicketActivity[]>([]);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] =
    useState<OrganisationTicket | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [updatingTicketId, setUpdatingTicketId] = useState("");
  const [isLoadingActivities, setIsLoadingActivities] = useState(false);

  const [error, setError] = useState("");
  const [membershipError, setMembershipError] = useState("");
  const [actionError, setActionError] = useState("");

  async function loadTickets(organisationId: string) {
    setIsLoading(true);
    setError("");

    try {
      const data = await getOrganisationTickets(organisationId);
      setTickets(data);
    } catch (err) {
      console.error("Failed to load tickets:", err);
      setError("Unable to load tickets. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedOrganisationId) {
      setTickets([]);
      setIsLoading(false);
      return;
    }

    let active = true;

    async function fetchTickets() {
      setIsLoading(true);
      setError("");

      try {
        const data = await getOrganisationTickets(selectedOrganisationId);

        if (active) {
          setTickets(data);
        }
      } catch (err) {
        console.error("Failed to load tickets:", err);

        if (active) {
          setError("Unable to load tickets. Please try again.");
          setTickets([]);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void fetchTickets();

    return () => {
      active = false;
    };
  }, [selectedOrganisationId]);

  useEffect(() => {
    if (!selectedOrganisationId) {
      setMembershipId("");
      return;
    }

    let active = true;

    async function fetchMembership() {
      setMembershipError("");

      try {
        const membership = await getMyOrganisationMembership(
          selectedOrganisationId,
        );

        if (active) {
          setMembershipId(membership.id);
        }
      } catch (err) {
        console.error("Failed to load organisation membership:", err);

        if (active) {
          setMembershipId("");
          setMembershipError(
            "Your active organisation membership could not be loaded.",
          );
        }
      }
    }

    void fetchMembership();

    return () => {
      active = false;
    };
  }, [selectedOrganisationId]);

  useEffect(() => {
    if (!selectedTicket) {
      setActivities([]);
      setIsLoadingActivities(false);
      return;
    }

    // Capture the ID before the asynchronous function.
    // This prevents TypeScript from treating selectedTicket as nullable.
    const ticketId = selectedTicket.id;

    let active = true;

    async function fetchActivities() {
      setIsLoadingActivities(true);
      setActionError("");

      try {
        const data = await getTicketActivities(ticketId);

        if (active) {
          setActivities(data);
        }
      } catch (err) {
        console.error("Failed to load ticket activities:", err);

        if (active) {
          setActivities([]);
          setActionError("Unable to load ticket activity history.");
        }
      } finally {
        if (active) {
          setIsLoadingActivities(false);
        }
      }
    }

    void fetchActivities();

    return () => {
      active = false;
    };
  }, [selectedTicket?.id]);

  async function handleCreateTicket(data: CreateTicketData): Promise<boolean> {
    if (!selectedOrganisationId || !membershipId) {
      setMembershipError(
        "Your organisation membership is not available. Please try refreshing.",
      );
      return false;
    }

    setIsCreating(true);
    setActionError("");

    try {
      const newTicket = await createOrganisationTicket(selectedOrganisationId, {
        requester_membership_id: membershipId,
        category_id: null,
        subject: data.subject,
        description: data.description,
        impact: data.impact,
        urgency: data.urgency,
        source: "WEB",
      });

      setTickets((previous) => [newTicket, ...previous]);
      setDialogOpen(false);

      return true;
    } catch (err) {
      console.error("Failed to create ticket:", err);
      setActionError(
        "Ticket creation failed. Please check your details and try again.",
      );

      return false;
    } finally {
      setIsCreating(false);
    }
  }

  async function handleStatusChange(ticketId: string, newStatus: string) {
    const currentTicket = tickets.find((ticket) => ticket.id === ticketId);

    if (
      !currentTicket ||
      currentTicket.status === newStatus ||
      updatingTicketId
    ) {
      return;
    }

    setUpdatingTicketId(ticketId);
    setActionError("");

    try {
      const updatedTicket = await updateTicket(ticketId, {
        status: newStatus,
      });

      setTickets((previous) =>
        previous.map((ticket) =>
          ticket.id === ticketId ? updatedTicket : ticket,
        ),
      );

      setSelectedTicket((previous) =>
        previous?.id === ticketId ? updatedTicket : previous,
      );
    } catch (err) {
      console.error("Failed to update ticket:", err);
      setActionError("Unable to update ticket status. Please try again.");
    } finally {
      setUpdatingTicketId("");
    }
  }

  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch = [
      ticket.ticket_number,
      ticket.subject,
      ticket.description,
      ticket.status,
      getPriorityLabel(ticket.priority),
    ]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "All" || ticket.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

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
      value: tickets.filter(
        (ticket) => ticket.status === "Resolved" || ticket.status === "Closed",
      ).length,
      icon: CheckCircle2,
      color: "text-green-600",
      background: "bg-green-500/10",
    },
  ];

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

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void loadTickets(selectedOrganisationId)}
            disabled={!selectedOrganisationId || isLoading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw
              className={`size-4 ${isLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </button>

          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            disabled={!selectedOrganisationId || !membershipId}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <Plus className="size-4" />
            Create Ticket
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => {
              if (selectedOrganisationId) {
                void loadTickets(selectedOrganisationId);
              }
            }}
            className="font-semibold underline"
          >
            Retry
          </button>
        </div>
      )}

      {membershipError && (
        <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 px-4 py-3 text-sm text-orange-700">
          {membershipError}
        </div>
      )}

      {actionError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-600">
          {actionError}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => {
          const Icon = card.icon;

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
                {isLoading ? "—" : card.value}
              </p>
            </div>
          );
        })}
      </div>

      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b p-5">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <h2 className="font-semibold">All Tickets</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Browse, search, filter and update support requests.
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
                  {availableStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[950px] text-left text-sm">
            <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-5 py-4 font-medium">Ticket</th>
                <th className="px-5 py-4 font-medium">Requester</th>
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
                    <button
                      type="button"
                      onClick={() => setSelectedTicket(ticket)}
                      className="text-left"
                    >
                      <span className="font-semibold text-primary hover:underline">
                        {ticket.ticket_number}
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {ticket.subject}
                      </span>
                    </button>
                  </td>

                  <td className="px-5 py-4 font-medium">
                    {ticket.requester_membership_id === membershipId
                      ? "You"
                      : "Organisation member"}
                  </td>

                  <td className="px-5 py-4">
                    <span className={getPriorityStyle(ticket.priority)}>
                      {getPriorityLabel(ticket.priority)}
                    </span>
                  </td>

                  <td className="px-5 py-4">
                    <select
                      value={ticket.status}
                      disabled={updatingTicketId === ticket.id}
                      onChange={(event) =>
                        void handleStatusChange(ticket.id, event.target.value)
                      }
                      aria-label={`Update status for ${ticket.ticket_number}`}
                      className={`rounded-full border-0 px-3 py-1.5 text-xs font-semibold outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50 ${getStatusStyle(ticket.status)}`}
                    >
                      {availableStatuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td className="px-5 py-4 text-muted-foreground">
                    {formatDate(ticket.created_at)}
                  </td>
                </tr>
              ))}

              {!isLoading && filteredTickets.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-5 py-12 text-center text-muted-foreground"
                  >
                    {tickets.length === 0
                      ? "No tickets exist in this organisation yet."
                      : "No tickets match your search or filter."}
                  </td>
                </tr>
              )}

              {isLoading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-5 py-12 text-center text-muted-foreground"
                  >
                    Loading tickets from ResolveIQ...
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
        isCreating={isCreating}
        onClose={() => setDialogOpen(false)}
        onCreate={handleCreateTicket}
      />

      {selectedTicket && (
        <div
          className="fixed inset-0 z-[110] flex items-center justify-center bg-black/50 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedTicket(null);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="ticket-details-title"
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-background shadow-xl"
          >
            <div className="flex items-center justify-between border-b p-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Ticket Details
                </p>
                <h2
                  id="ticket-details-title"
                  className="mt-1 text-xl font-bold"
                >
                  {selectedTicket.ticket_number}
                </h2>
              </div>

              <button
                type="button"
                onClick={() => setSelectedTicket(null)}
                aria-label="Close ticket details"
                className="rounded-lg p-2 text-muted-foreground hover:bg-accent"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="space-y-6 p-5">
              <div>
                <h3 className="text-lg font-semibold">
                  {selectedTicket.subject}
                </h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                  {selectedTicket.description}
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Requester</p>
                  <p className="mt-1 font-semibold">
                    {selectedTicket.requester_membership_id === membershipId
                      ? "You"
                      : "Organisation member"}
                  </p>
                </div>

                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Priority</p>
                  <p
                    className={`mt-1 font-semibold ${getPriorityStyle(selectedTicket.priority)}`}
                  >
                    {getPriorityLabel(selectedTicket.priority)}
                  </p>
                </div>

                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Impact</p>
                  <p className="mt-1 font-semibold">{selectedTicket.impact}</p>
                </div>

                <div className="rounded-lg border p-4">
                  <p className="text-xs text-muted-foreground">Urgency</p>
                  <p className="mt-1 font-semibold">{selectedTicket.urgency}</p>
                </div>

                <div className="rounded-lg border p-4 sm:col-span-2">
                  <p className="text-xs text-muted-foreground">Created Date</p>
                  <p className="mt-1 font-semibold">
                    {formatDateTime(selectedTicket.created_at)}
                  </p>
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <label
                  htmlFor="details-ticket-status"
                  className="text-sm font-semibold"
                >
                  Ticket Status
                </label>

                <select
                  id="details-ticket-status"
                  value={selectedTicket.status}
                  disabled={updatingTicketId === selectedTicket.id}
                  onChange={(event) =>
                    void handleStatusChange(
                      selectedTicket.id,
                      event.target.value,
                    )
                  }
                  className={`mt-2 w-full rounded-lg border px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-primary/30 ${getStatusStyle(selectedTicket.status)}`}
                >
                  {availableStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>

              {actionError && (
                <p className="text-sm text-red-600">{actionError}</p>
              )}

              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <History className="size-5 text-primary" />
                  <div>
                    <h3 className="font-semibold">Activity History</h3>
                    <p className="text-xs text-muted-foreground">
                      Actual events recorded by ResolveIQ
                    </p>
                  </div>
                </div>

                {isLoadingActivities ? (
                  <p className="text-sm text-muted-foreground">
                    Loading activity history...
                  </p>
                ) : (
                  <div className="relative space-y-5 border-l-2 border-muted pl-5">
                    {activities.map((activity) => (
                      <div key={activity.id} className="relative">
                        <span className="absolute -left-[27px] top-1 flex size-4 items-center justify-center rounded-full border-2 border-background bg-primary">
                          <Activity className="size-2 text-primary-foreground" />
                        </span>

                        <p className="text-sm font-medium">
                          {activity.description}
                        </p>

                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatDateTime(activity.created_at)}
                        </p>
                      </div>
                    ))}

                    {activities.length === 0 && (
                      <p className="text-sm text-muted-foreground">
                        No activity recorded yet.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end border-t p-5">
              <button
                type="button"
                onClick={() => setSelectedTicket(null)}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                <Eye className="size-4" />
                Close Details
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
