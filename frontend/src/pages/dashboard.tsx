import { useEffect, useState } from "react";
import {
  Ticket,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Plus,
  Activity,
  ShieldCheck,
  Zap,
  Clock,
  RefreshCw,
} from "lucide-react";
import { Link } from "react-router-dom";

import { getSLADashboard, type SLADashboard } from "@/services/dashboard";

import { useOrganisation } from "@/contexts/organisation-context";

function Dashboard() {
  const {
    organisations,
    selectedOrganisationId,
    setSelectedOrganisationId,
    isLoadingOrganisations,
  } = useOrganisation();

  const [slaData, setSlaData] = useState<SLADashboard | null>(null);
  const [isLoadingSLA, setIsLoadingSLA] = useState(false);
  const [error, setError] = useState("");

  // Load SLA statistics whenever the selected organisation changes.
  useEffect(() => {
    if (!selectedOrganisationId) {
      setSlaData(null);
      return;
    }

    let active = true;

    async function loadSLA() {
      try {
        setIsLoadingSLA(true);
        setError("");
        setSlaData(null);

        const data = await getSLADashboard(selectedOrganisationId);

        if (active) {
          setSlaData(data);
        }
      } catch {
        if (active) {
          setError(
            "Unable to load SLA statistics. Please ensure you are signed in with an OWNER or ADMIN account.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingSLA(false);
        }
      }
    }

    void loadSLA();

    return () => {
      active = false;
    };
  }, [selectedOrganisationId]);

  const stats = [
    {
      title: "Total Tickets",
      value: slaData ? slaData.total_tickets.toLocaleString() : "—",
      description: "Tickets in this organisation",
      icon: Ticket,
      iconStyle: "bg-blue-50 text-blue-600",
    },
    {
      title: "Response Compliance",
      value: slaData ? `${slaData.response_compliance_percent}%` : "—",
      description: "SLA response compliance",
      icon: Clock,
      iconStyle: "bg-violet-50 text-violet-600",
    },
    {
      title: "Resolution Compliance",
      value: slaData ? `${slaData.resolution_compliance_percent}%` : "—",
      description: "SLA resolution compliance",
      icon: CheckCircle2,
      iconStyle: "bg-emerald-50 text-emerald-600",
    },
    {
      title: "Response Breaches",
      value: slaData ? slaData.response.breached.toLocaleString() : "—",
      description: "Tickets exceeding response SLA",
      icon: AlertCircle,
      iconStyle: "bg-amber-50 text-amber-600",
    },
  ];

  return (
    <div className="space-y-7">
      {/* Welcome section */}
      <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
              Operations overview
            </span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Dashboard Overview
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Monitor your support performance and keep operations running
            smoothly.
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <select
            value={selectedOrganisationId}
            onChange={(event) => setSelectedOrganisationId(event.target.value)}
            disabled={isLoadingOrganisations || organisations.length === 0}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoadingOrganisations ? (
              <option value="">Loading organisations...</option>
            ) : (
              organisations.map((organisation) => (
                <option key={organisation.id} value={organisation.id}>
                  {organisation.name}
                </option>
              ))
            )}
          </select>

          <Link
            to="/tickets"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition-all hover:-translate-y-0.5 hover:bg-blue-700 hover:shadow-blue-600/30"
          >
            <Plus className="size-4" />
            Create Ticket
          </Link>
        </div>
      </section>

      {/* Error message */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-rose-600" />
          <div>
            <p className="text-sm font-semibold text-rose-800">
              Dashboard data unavailable
            </p>
            <p className="mt-1 text-xs leading-relaxed text-rose-700">
              {error}
            </p>
          </div>
        </div>
      )}

      {/* KPI cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div
              key={stat.title}
              className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/30 transition-all duration-200 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg hover:shadow-slate-200/50"
            >
              <div className="flex items-center justify-between">
                <p className="text-[13px] font-medium text-slate-500">
                  {stat.title}
                </p>

                <div className={`rounded-xl p-2.5 ${stat.iconStyle}`}>
                  <Icon className="size-[18px]" />
                </div>
              </div>

              <p className="mt-5 text-3xl font-bold tracking-tight text-slate-900">
                {isLoadingSLA ? (
                  <span className="inline-block h-9 w-16 animate-pulse rounded-lg bg-slate-100" />
                ) : (
                  stat.value
                )}
              </p>

              <p className="mt-3 text-xs text-slate-400">{stat.description}</p>
            </div>
          );
        })}
      </section>

      {/* Main dashboard content */}
      <section className="grid gap-5 xl:grid-cols-3">
        {/* SLA overview */}
        <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-200/30 xl:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-5 sm:px-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                SLA Performance
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                Response and resolution performance
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700">
              <Activity className="size-3.5" />
              Live backend data
            </div>
          </div>

          <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
            {/* Response SLA */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-700">
                  Response SLA
                </p>
                <Clock className="size-4 text-blue-600" />
              </div>

              {isLoadingSLA ? (
                <div className="mt-5 h-8 w-20 animate-pulse rounded bg-slate-200" />
              ) : (
                <p className="mt-4 text-3xl font-bold text-slate-900">
                  {slaData ? `${slaData.response_compliance_percent}%` : "—"}
                </p>
              )}

              <div className="mt-5 space-y-3">
                {[
                  {
                    label: "On track",
                    value: slaData?.response.on_track,
                    color: "bg-blue-500",
                  },
                  {
                    label: "At risk",
                    value: slaData?.response.at_risk,
                    color: "bg-amber-500",
                  },
                  {
                    label: "Breached",
                    value: slaData?.response.breached,
                    color: "bg-rose-500",
                  },
                  {
                    label: "Met",
                    value: slaData?.response.met,
                    color: "bg-emerald-500",
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2 text-slate-500">
                      <span className={`size-2 rounded-full ${item.color}`} />
                      {item.label}
                    </div>
                    <span className="font-semibold tabular-nums text-slate-700">
                      {isLoadingSLA ? "—" : (item.value ?? "—")}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Resolution SLA */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-700">
                  Resolution SLA
                </p>
                <CheckCircle2 className="size-4 text-emerald-600" />
              </div>

              {isLoadingSLA ? (
                <div className="mt-5 h-8 w-20 animate-pulse rounded bg-slate-200" />
              ) : (
                <p className="mt-4 text-3xl font-bold text-slate-900">
                  {slaData ? `${slaData.resolution_compliance_percent}%` : "—"}
                </p>
              )}

              <div className="mt-5 space-y-3">
                {[
                  {
                    label: "On track",
                    value: slaData?.resolution.on_track,
                    color: "bg-blue-500",
                  },
                  {
                    label: "At risk",
                    value: slaData?.resolution.at_risk,
                    color: "bg-amber-500",
                  },
                  {
                    label: "Breached",
                    value: slaData?.resolution.breached,
                    color: "bg-rose-500",
                  },
                  {
                    label: "Met",
                    value: slaData?.resolution.met,
                    color: "bg-emerald-500",
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2 text-slate-500">
                      <span className={`size-2 rounded-full ${item.color}`} />
                      {item.label}
                    </div>
                    <span className="font-semibold tabular-nums text-slate-700">
                      {isLoadingSLA ? "—" : (item.value ?? "—")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="border-t border-slate-100 px-6 py-3">
            <p className="text-[11px] text-slate-400">
              SLA statistics retrieved from your ResolveIQ backend.
            </p>
          </div>
        </div>

        {/* AI Operations panel */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/30 sm:p-6">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-md shadow-blue-500/20">
              <Sparkles className="size-5" />
            </div>

            <div>
              <h2 className="text-base font-bold text-slate-900">
                AI Operations
              </h2>
              <p className="text-[11px] text-slate-400">
                Intelligence overview
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/60 p-4">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-blue-600" />
              <span className="text-xs font-bold text-blue-900">
                AI development status
              </span>
            </div>

            <p className="mt-2 text-[11px] leading-relaxed text-slate-600">
              AI categorization, priority prediction and knowledge
              recommendations are planned capabilities. Live AI performance
              measurements are not yet connected.
            </p>
          </div>

          <div className="mt-6 rounded-xl border border-emerald-100 bg-emerald-50/70 p-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-emerald-600" />
              <p className="text-xs font-bold text-emerald-900">
                Operations insight
              </p>
            </div>

            <p className="mt-2 text-[11px] leading-relaxed text-emerald-800/80">
              Monitor response and resolution SLA performance to identify
              tickets that need attention.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom information cards */}
      <section className="grid gap-4 sm:grid-cols-2">
        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/30">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
            <Zap className="size-5" />
          </div>

          <div>
            <p className="text-sm font-bold text-slate-800">
              Smarter support operations
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Bring tickets, SLAs and escalation workflows together.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-slate-200/30">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
            <ShieldCheck className="size-5" />
          </div>

          <div>
            <p className="text-sm font-bold text-slate-800">
              Operational visibility
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Track service performance and support activity in one place.
            </p>
          </div>
        </div>
      </section>

      {isLoadingSLA && (
        <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
          <RefreshCw className="size-3.5 animate-spin" />
          Updating dashboard statistics...
        </div>
      )}
    </div>
  );
}

export { Dashboard };
