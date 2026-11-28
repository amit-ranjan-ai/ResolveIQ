import { useState, type FormEvent } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Sparkles,
  Ticket,
  X,
} from "lucide-react";

import {
  classifyTicket,
  type TicketClassificationResponse,
} from "../../services/ai";

export interface CreateTicketData {
  subject: string;
  description: string;
  impact: "LOW" | "MEDIUM" | "HIGH";
  urgency: "LOW" | "MEDIUM" | "HIGH";
  category_id: string | null;
}

interface CreateTicketDialogProps {
  open: boolean;
  isCreating: boolean;
  organisationId: string;
  onClose: () => void;
  onCreate: (ticket: CreateTicketData) => Promise<boolean> | boolean;
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 70) return "text-emerald-600";
  if (confidence >= 40) return "text-amber-600";
  return "text-muted-foreground";
}

function ConfidenceLabel({ confidence }: { confidence: number }) {
  return (
    <span className={`text-xs font-semibold ${getConfidenceColor(confidence)}`}>
      {confidence}% confidence
    </span>
  );
}

export function CreateTicketDialog({
  open,
  isCreating,
  organisationId,
  onClose,
  onCreate,
}: CreateTicketDialogProps) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [impact, setImpact] = useState<"LOW" | "MEDIUM" | "HIGH">("MEDIUM");
  const [urgency, setUrgency] = useState<"LOW" | "MEDIUM" | "HIGH">("MEDIUM");
  const [categoryId, setCategoryId] = useState<string | null>(null);

  const [classification, setClassification] =
    useState<TicketClassificationResponse | null>(null);

  const [isClassifying, setIsClassifying] = useState(false);
  const [classificationError, setClassificationError] = useState("");
  const [suggestionsApplied, setSuggestionsApplied] = useState(false);

  if (!open) return null;

  function resetClassification() {
    setClassification(null);
    setClassificationError("");
    setSuggestionsApplied(false);
    setCategoryId(null);
  }

  async function handleClassify() {
    if (
      !organisationId ||
      subject.trim().length < 3 ||
      description.trim().length < 5 ||
      isClassifying ||
      isCreating
    ) {
      return;
    }

    setIsClassifying(true);
    setClassificationError("");
    setSuggestionsApplied(false);
    setClassification(null);
    setCategoryId(null);

    try {
      const result = await classifyTicket(organisationId, {
        subject: subject.trim(),
        description: description.trim(),
      });

      setClassification(result);
    } catch (error) {
      console.error("AI ticket classification failed:", error);

      setClassificationError(
        "Unable to classify this ticket. You can still create it manually.",
      );
    } finally {
      setIsClassifying(false);
    }
  }

  function handleApplySuggestions() {
    if (!classification) return;

    if (
      classification.impact.value === "LOW" ||
      classification.impact.value === "MEDIUM" ||
      classification.impact.value === "HIGH"
    ) {
      setImpact(classification.impact.value);
    }

    if (
      classification.urgency.value === "LOW" ||
      classification.urgency.value === "MEDIUM" ||
      classification.urgency.value === "HIGH"
    ) {
      setUrgency(classification.urgency.value);
    }

    setCategoryId(classification.category.category_id);
    setSuggestionsApplied(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isCreating || isClassifying) return;

    const success = await onCreate({
      subject: subject.trim(),
      description: description.trim(),
      impact,
      urgency,
      category_id: categoryId,
    });

    if (!success) return;

    setSubject("");
    setDescription("");
    setImpact("MEDIUM");
    setUrgency("MEDIUM");
    setCategoryId(null);
    setClassification(null);
    setClassificationError("");
    setSuggestionsApplied(false);
  }

  const priority = classification?.priority;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget &&
          !isCreating &&
          !isClassifying
        ) {
          onClose();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-ticket-title"
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border bg-background shadow-xl"
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
            disabled={isCreating || isClassifying}
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
              disabled={isCreating || isClassifying}
              value={subject}
              onChange={(event) => {
                setSubject(event.target.value);
                resetClassification();
              }}
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
              disabled={isCreating || isClassifying}
              value={description}
              onChange={(event) => {
                setDescription(event.target.value);
                resetClassification();
              }}
              placeholder="Provide details about the issue..."
              className="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
            />
          </div>

          <div className="rounded-xl border bg-muted/20 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Sparkles className="size-5" />
                </div>

                <div>
                  <h3 className="text-sm font-semibold">
                    AI Ticket Classification
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Analyze the issue and get category, impact, urgency,
                    priority and team recommendations.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => void handleClassify()}
                disabled={
                  isCreating ||
                  isClassifying ||
                  subject.trim().length < 3 ||
                  description.trim().length < 5 ||
                  !organisationId
                }
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isClassifying ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Sparkles className="size-4" />
                )}
                {isClassifying ? "Analyzing..." : "Suggest with AI"}
              </button>
            </div>

            {classificationError && (
              <div
                role="alert"
                className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {classificationError}
              </div>
            )}

            {classification && (
              <div className="mt-4 space-y-4 border-t pt-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-semibold">
                      Classification Results
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Overall heuristic confidence:{" "}
                      {classification.overall_confidence}%
                    </p>
                  </div>

                  <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-700 dark:text-amber-400">
                    Human review required
                  </span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Category</p>
                    <p className="mt-1 text-sm font-semibold">
                      {classification.category.category_name ?? "No suggestion"}
                    </p>
                    <ConfidenceLabel
                      confidence={classification.category.confidence}
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      {classification.category.explanation}
                    </p>
                  </div>

                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Priority</p>
                    <p className="mt-1 text-sm font-semibold">
                      {priority ?? "Unavailable"}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Calculated from suggested impact and urgency.
                    </p>
                  </div>

                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Impact</p>
                    <p className="mt-1 text-sm font-semibold">
                      {classification.impact.value ?? "No suggestion"}
                    </p>
                    <ConfidenceLabel
                      confidence={classification.impact.confidence}
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      {classification.impact.explanation}
                    </p>
                  </div>

                  <div className="rounded-lg border bg-background p-3">
                    <p className="text-xs text-muted-foreground">Urgency</p>
                    <p className="mt-1 text-sm font-semibold">
                      {classification.urgency.value ?? "No suggestion"}
                    </p>
                    <ConfidenceLabel
                      confidence={classification.urgency.confidence}
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      {classification.urgency.explanation}
                    </p>
                  </div>

                  <div className="rounded-lg border bg-background p-3 sm:col-span-2">
                    <p className="text-xs text-muted-foreground">
                      Recommended Team
                    </p>
                    <p className="mt-1 text-sm font-semibold">
                      {classification.team.team_name ??
                        "No team recommendation"}
                    </p>
                    <ConfidenceLabel
                      confidence={classification.team.confidence}
                    />
                    <p className="mt-2 text-xs text-muted-foreground">
                      {classification.team.explanation}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      This is a recommendation only. No team will be assigned
                      automatically.
                    </p>
                  </div>
                </div>

                {classification.fields_requiring_review.length > 0 && (
                  <p className="text-xs text-amber-700 dark:text-amber-400">
                    Review recommended for:{" "}
                    {classification.fields_requiring_review.join(", ")}.
                  </p>
                )}

                <button
                  type="button"
                  onClick={handleApplySuggestions}
                  disabled={isCreating || !classification}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
                >
                  <CheckCircle2 className="size-4" />
                  Apply AI Suggestions
                </button>

                {suggestionsApplied && (
                  <p className="flex items-center gap-2 text-xs font-medium text-emerald-600">
                    <CheckCircle2 className="size-4" />
                    Suggestions applied. You can still edit the values below.
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="ticket-impact" className="text-sm font-medium">
                Impact
              </label>

              <select
                id="ticket-impact"
                value={impact}
                disabled={isCreating || isClassifying}
                onChange={(event) => {
                  setImpact(event.target.value as "LOW" | "MEDIUM" | "HIGH");
                  setSuggestionsApplied(false);
                }}
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
                disabled={isCreating || isClassifying}
                onChange={(event) => {
                  setUrgency(event.target.value as "LOW" | "MEDIUM" | "HIGH");
                  setSuggestionsApplied(false);
                }}
                className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>
          </div>

          {categoryId && (
            <p className="text-xs text-emerald-600">
              AI category suggestion will be included when creating this ticket.
            </p>
          )}

          <p className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
            Ticket priority is calculated automatically by the backend based on
            the final impact and urgency values you select.
          </p>

          <div className="flex flex-col-reverse justify-end gap-3 border-t pt-5 sm:flex-row">
            <button
              type="button"
              onClick={onClose}
              disabled={isCreating || isClassifying}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isCreating || isClassifying}
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
