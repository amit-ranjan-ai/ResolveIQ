
import { useState } from "react"
import { X, Ticket } from "lucide-react"

export interface CreateTicketData {
  subject: string
  description: string
  category: string
  priority: string
  requester: string
}

interface CreateTicketDialogProps {
  open: boolean
  onClose: () => void
  onCreate: (ticket: CreateTicketData) => void
}

export function CreateTicketDialog({
  open,
  onClose,
  onCreate,
}: CreateTicketDialogProps) {
  const [subject, setSubject] = useState("")
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState("Software")
  const [priority, setPriority] = useState("Medium")
  const [requester, setRequester] = useState("")

  if (!open) return null

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    onCreate({
      subject: subject.trim(),
      description: description.trim(),
      category,
      priority,
      requester: requester.trim(),
    })

    setSubject("")
    setDescription("")
    setCategory("Software")
    setPriority("Medium")
    setRequester("")
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-ticket-title"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl border bg-background shadow-xl"
      >
        <div className="flex items-center justify-between border-b p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Ticket className="size-5" />
            </div>

            <div>
              <h2
                id="create-ticket-title"
                className="font-semibold"
              >
                Create New Ticket
              </h2>
              <p className="text-xs text-muted-foreground">
                Submit a new internal IT support request.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="size-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-5">
          <div className="space-y-2">
            <label htmlFor="ticket-subject" className="text-sm font-medium">
              Ticket Subject
            </label>

            <input
              id="ticket-subject"
              required
              maxLength={150}
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder="Briefly describe your issue"
              className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="ticket-description" className="text-sm font-medium">
              Description
            </label>

            <textarea
              id="ticket-description"
              required
              maxLength={2000}
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Provide details about the issue..."
              className="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="ticket-category" className="text-sm font-medium">
                Category
              </label>

              <select
                id="ticket-category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
              >
                <option value="Network">Network</option>
                <option value="Hardware">Hardware</option>
                <option value="Software">Software</option>
                <option value="Access">Access</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="ticket-priority" className="text-sm font-medium">
                Priority
              </label>

              <select
                id="ticket-priority"
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="ticket-requester" className="text-sm font-medium">
              Requester Name
            </label>

            <input
              id="ticket-requester"
              required
              maxLength={100}
              value={requester}
              onChange={(event) => setRequester(event.target.value)}
              placeholder="Enter employee name"
              className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <div className="flex flex-col-reverse justify-end gap-3 border-t pt-5 sm:flex-row">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              Cancel
            </button>

            <button
              type="submit"
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Create Ticket
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
