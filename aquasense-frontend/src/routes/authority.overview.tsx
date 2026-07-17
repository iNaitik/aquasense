import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Droplets,
  Loader2,
  MapPin,
  MessagesSquare,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchPipelineStats } from "@/lib/api";
import { getComplaintStats } from "@/lib/api/admin-complaints";

export const Route = createFileRoute("/authority/overview")({
  head: () => ({
    meta: [
      { title: "Authority Overview — AQUA-SENSE" },
      {
        name: "description",
        content:
          "Combined overview of pipeline risk and citizen complaints for Indore water infrastructure.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: OverviewPage,
});

function Stat({
  label,
  value,
  accent,
  loading,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  accent?: string;
  loading?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
          </div>
          {icon}
        </div>
        <div className={`mt-2 text-2xl font-bold ${accent ?? ""}`}>
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : value}
        </div>
      </CardContent>
    </Card>
  );
}

function OverviewPage() {
  const pipeStats = useQuery({
    queryKey: ["pipelines", "stats"],
    queryFn: fetchPipelineStats,
    staleTime: 5 * 60_000,
  });
  const complaintStats = useQuery({
    queryKey: ["admin-complaints", "stats"],
    queryFn: getComplaintStats,
    staleTime: 60_000,
  });

  const p = pipeStats.data;
  const c = complaintStats.data;

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-4">
      {/* Pipelines */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            <Droplets className="h-4 w-4" /> Pipeline Infrastructure
          </h2>
          {pipeStats.isError && (
            <span className="text-xs text-destructive">Backend unreachable</span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat
            label="Total Pipelines"
            value={p?.total_pipelines ?? "—"}
            loading={pipeStats.isLoading}
            icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
          />
          <Stat
            label="High Risk"
            value={p?.high_risk ?? "—"}
            accent="text-red-600"
            loading={pipeStats.isLoading}
            icon={<AlertTriangle className="h-4 w-4 text-red-600" />}
          />
          <Stat
            label="Medium Risk"
            value={p?.medium_risk ?? "—"}
            accent="text-amber-600"
            loading={pipeStats.isLoading}
          />
          <Stat
            label="Low Risk"
            value={p?.low_risk ?? "—"}
            accent="text-green-600"
            loading={pipeStats.isLoading}
          />
        </div>
      </section>

      {/* Complaints */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            <MessagesSquare className="h-4 w-4" /> Citizen Complaints
          </h2>
          {complaintStats.isError && (
            <span className="text-xs text-destructive">Backend unreachable</span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat
            label="Total Complaints"
            value={c?.total_complaints ?? "—"}
            loading={complaintStats.isLoading}
          />
          <Stat
            label="Submitted"
            value={c?.submitted ?? "—"}
            accent="text-blue-600"
            loading={complaintStats.isLoading}
          />
          <Stat
            label="Open Complaints"
            value={
              c?.open_complaints ??
              (c
                ? (c.submitted ?? 0) + (c.reviewed ?? 0) + (c.assigned ?? 0)
                : "—")
            }
            accent="text-amber-600"
            loading={complaintStats.isLoading}
          />
          <Stat
            label="Resolved"
            value={c?.resolved ?? "—"}
            accent="text-green-600"
            loading={complaintStats.isLoading}
          />
        </div>
      </section>

      {/* Quick actions */}
      <section className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <div className="font-semibold">Pipeline Risk Map</div>
              <p className="text-sm text-muted-foreground">
                Explore the 750-segment Indore network with ML risk predictions.
              </p>
            </div>
            <Button asChild>
              <Link to="/authority/dashboard">
                View Risk Map <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <div className="font-semibold">Citizen Complaints</div>
              <p className="text-sm text-muted-foreground">
                Triage submissions, update status and manage resolutions.
              </p>
            </div>
            <Button asChild>
              <Link to="/authority/complaints">
                Manage Complaints <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
