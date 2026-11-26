import { useState, type FormEvent } from "react";
import { Loader2, Ticket, X } from "lucide-react";

export interface CreateTicketData {
  subject: string;
  description: string;
  impact: "LOW" | "MEDIUM" | "HIGH";
  urgency: "LOW" | "MEDIUM" | "HIGH";
}

interface CreateTicketDialogProps {
  open: boolean;
  isCreating: boolean;
  onClose: () => void;
  onCreate: (ticket: CreateTicketData) => Promise<boolean> | boolean;
}

export function CreateTicketDialog({
  open,
  isCreating,
  onClose,
  onCreate,
}: CreateTicketDialogProps) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [impact, setImpact] = useState<"LOW" | "MEDIUM" | "HIGH">("MEDIUM");
  const [urgency, setUrgency] = useState<"LOW" | "MEDIUM" | "HIGH">("MEDIUM");

  if (!open) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isCreating) return;

    const success = await onCreate({
      subject: subject.trim(),
      description: description.trim(),
      impact,
      urgency,
    });

    if (!success) return;

    setSubject("");
    setDescription("");
    setImpact("MEDIUM");
    setUrgency("MEDIUM");
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isCreating) {
          onClose();
        }
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
              <h2 id="create-ticket-title" className="font-semibold">
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
            disabled={isCreating}
            aria-label="Close dialog"
            className="rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
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
              minLength={3}
              maxLength={200}
              disabled={isCreating}
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder="Briefly describe your issue"
              className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="ticket-description" className="text-sm font-medium">
              Description
            </label>

            <textarea
              id="ticket-description"
              required
              minLength={5}
              rows={4}
              disabled={isCreating}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Provide details about the issue..."
              className="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="ticket-impact" className="text-sm font-medium">
                Impact
              </label>

              <select
                id="ticket-impact"
                value={impact}
                disabled={isCreating}
                onChange={(event) =>
                  setImpact(event.target.value as "LOW" | "MEDIUM" | "HIGH")
                }
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="ticket-urgency" className="text-sm font-medium">
                Urgency
              </label>

              <select
                id="ticket-urgency"
                value={urgency}
                disabled={isCreating}
                onChange={(event) =>
                  setUrgency(event.target.value as "LOW" | "MEDIUM" | "HIGH")
                }
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>
          </div>

          <p className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
            Ticket priority will be calculated automatically based on the
            selected impact and urgency.
          </p>

          <div className="flex flex-col-reverse justify-end gap-3 border-t pt-5 sm:flex-row">
            <button
              type="button"
              onClick={onClose}
              disabled={isCreating}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isCreating}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCreating && <Loader2 className="size-4 animate-spin" />}
              {isCreating ? "Creating..." : "Create Ticket"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
