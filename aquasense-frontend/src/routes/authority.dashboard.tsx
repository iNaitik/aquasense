import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Droplets, Loader2, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  fetchPipelines,
  fetchPipelineStats,
  type PipelineListItem,
  type RiskLevel,
} from "@/lib/api";
import { PipelineDetailPanel } from "@/components/authority/PipelineDetailPanel";

const RiskMap = lazy(() => import("@/components/authority/RiskMap"));

export const Route = createFileRoute("/authority/dashboard")({
  head: () => ({
    meta: [
      { title: "Authority Pipeline Risk Dashboard — AQUA-SENSE" },
      {
        name: "description",
        content:
          "Interactive municipal dashboard for identifying high-risk water pipeline segments in Indore.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AuthorityDashboard,
});

type Filter = "ALL" | RiskLevel;

function StatCard({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  accent?: string;
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
        <div className={`mt-2 text-2xl font-bold ${accent ?? ""}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

function ClientOnly({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return <>{children}</>;
}

function AuthorityDashboard() {
  const [filter, setFilter] = useState<Filter>("ALL");
  const [selected, setSelected] = useState<PipelineListItem | null>(null);
  const [focusPipeline, setFocusPipeline] = useState<PipelineListItem | null>(
    null,
  );

  const pipelinesQuery = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => fetchPipelines(),
    staleTime: 5 * 60_000,
  });

  const statsQuery = useQuery({
    queryKey: ["pipelines", "stats"],
    queryFn: fetchPipelineStats,
    staleTime: 5 * 60_000,
  });

  const pipelines = pipelinesQuery.data ?? [];

  const filtered = useMemo(() => {
    if (filter === "ALL") return pipelines;
    return pipelines.filter((p) => p.risk_level === filter);
  }, [pipelines, filter]);

  const topRisk = useMemo(
    () =>
      [...pipelines]
        .sort((a, b) => b.risk_score - a.risk_score)
        .slice(0, 10),
    [pipelines],
  );

  const handleSelect = (p: PipelineListItem, focus = false) => {
    setSelected(p);
    if (focus) setFocusPipeline({ ...p });
  };

  const stats = statsQuery.data;

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4">
      {/* Summary Cards */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard
          label="Total Pipelines"
          value={
            statsQuery.isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              (stats?.total_pipelines ?? "—")
            )
          }
          icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          label="High Risk"
          value={stats?.high_risk ?? "—"}
          accent="text-red-600"
          icon={<AlertTriangle className="h-4 w-4 text-red-600" />}
        />
        <StatCard
          label="Medium Risk"
          value={stats?.medium_risk ?? "—"}
          accent="text-amber-600"
        />
        <StatCard
          label="Low Risk"
          value={stats?.low_risk ?? "—"}
          accent="text-green-600"
        />
        <StatCard
          label="Avg Risk Score"
          value={
            stats?.average_risk_score != null
              ? Number(stats.average_risk_score).toFixed(2)
              : "—"
          }
        />
      </section>

      {/* Filters */}
      <section className="flex flex-wrap items-center gap-2">
        {(["ALL", "HIGH", "MEDIUM", "LOW"] as const).map((f) => (
          <Button
            key={f}
            size="sm"
            variant={filter === f ? "default" : "outline"}
            onClick={() => setFilter(f)}
          >
            {f === "ALL" ? "All" : `${f[0]}${f.slice(1).toLowerCase()} Risk`}
          </Button>
        ))}
        <div className="ml-auto text-sm text-muted-foreground">
          Showing{" "}
          <span className="font-semibold text-foreground">
            {filtered.length}
          </span>{" "}
          of {pipelines.length} segments
        </div>
      </section>

      {/* Map + Details */}
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="relative lg:col-span-2">
          <div className="relative h-[520px] w-full overflow-hidden rounded-lg border bg-muted">
            {pipelinesQuery.isLoading && (
              <div className="absolute inset-0 z-[500] flex items-center justify-center bg-background/70">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            )}
            {pipelinesQuery.isError && (
              <div className="absolute inset-0 z-[500] flex items-center justify-center p-6 text-center">
                <div>
                  <AlertTriangle className="mx-auto h-8 w-8 text-destructive" />
                  <p className="mt-2 font-medium">
                    Unable to load pipeline risk data.
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Please try again shortly.
                  </p>
                  <Button
                    size="sm"
                    className="mt-3"
                    onClick={() => pipelinesQuery.refetch()}
                  >
                    Retry
                  </Button>
                </div>
              </div>
            )}
            {!pipelinesQuery.isLoading &&
              !pipelinesQuery.isError &&
              filtered.length === 0 && (
                <div className="absolute inset-x-0 top-4 z-[500] mx-auto w-fit rounded-md bg-background/90 px-3 py-1.5 text-sm shadow">
                  No pipelines match the current filter.
                </div>
              )}
            <ClientOnly>
              <Suspense fallback={null}>
                <RiskMap
                  pipelines={filtered}
                  selectedId={selected?.pipeline_id ?? null}
                  onSelect={(p) => handleSelect(p)}
                  focusPipeline={focusPipeline}
                />
              </Suspense>
            </ClientOnly>

            {/* Legend */}
            <div className="absolute bottom-3 left-3 z-[500] rounded-md border bg-background/95 p-3 text-xs shadow">
              <div className="mb-1 font-semibold">Risk Legend</div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1 w-6 rounded bg-green-600" />
                Low
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1 w-6 rounded bg-amber-500" />
                Medium
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1 w-6 rounded bg-red-600" />
                High
              </div>
              <div className="mt-1 max-w-[180px] text-muted-foreground">
                ML-generated prototype estimates.
              </div>
            </div>
          </div>
        </div>

        <div className="h-[520px] overflow-hidden rounded-lg border bg-card">
          <PipelineDetailPanel
            pipeline={selected}
            onClose={() => setSelected(null)}
          />
        </div>
      </section>

      {/* Highest Risk List */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Highest Risk Pipelines
        </h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {topRisk.map((p) => (
            <button
              key={p.pipeline_id}
              onClick={() => handleSelect(p, true)}
              className={`rounded-md border p-3 text-left transition-colors hover:border-primary hover:bg-accent ${
                selected?.pipeline_id === p.pipeline_id
                  ? "border-primary bg-accent"
                  : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm font-semibold">
                  {p.pipeline_id}
                </span>
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{
                    background:
                      p.risk_level === "HIGH"
                        ? "#dc2626"
                        : p.risk_level === "MEDIUM"
                          ? "#f59e0b"
                          : "#16a34a",
                  }}
                />
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {p.risk_level} · score {p.risk_score.toFixed(2)}
              </div>
            </button>
          ))}
          {topRisk.length === 0 && !pipelinesQuery.isLoading && (
            <div className="text-sm text-muted-foreground">
              No pipeline data available.
            </div>
          )}
        </div>
      </section>

      {/* Disclaimer */}
      <p className="text-xs leading-relaxed text-muted-foreground">
        This dashboard uses a simulated Indore pipeline network and an ML model
        trained on synthetic historical data. Risk scores are prototype
        estimates and do not represent official municipal infrastructure
        assessments.
      </p>
    </main>
  );
}
