import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  fetchPipelineDetail,
  type PipelineDetail,
  type PipelineListItem,
  type RiskLevel,
} from "@/lib/api";

function levelBadgeClass(level: RiskLevel) {
  switch (level) {
    case "HIGH":
      return "bg-red-600 text-white hover:bg-red-600";
    case "MEDIUM":
      return "bg-amber-500 text-white hover:bg-amber-500";
    default:
      return "bg-green-600 text-white hover:bg-green-600";
  }
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/60 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground text-right">{value}</span>
    </div>
  );
}

function fmt(v: unknown, suffix = "") {
  if (v === null || v === undefined || v === "") return "—";
  return `${v}${suffix}`;
}

export function PipelineDetailPanel({
  pipeline,
  onClose,
}: {
  pipeline: PipelineListItem | null;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<PipelineDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pipeline) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setDetail(null);
    fetchPipelineDetail(pipeline.pipeline_id)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pipeline]);

  if (!pipeline) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center text-sm text-muted-foreground">
        <p>Select a pipeline segment on the map to inspect its risk profile.</p>
      </div>
    );
  }

  const isHigh = pipeline.risk_level === "HIGH";
  const failureProb =
    detail?.failure_probability != null
      ? `${(Number(detail.failure_probability) * 100).toFixed(1)}%`
      : "—";

  return (
    <div className="flex h-full flex-col">
      <div
        className={`flex items-start justify-between gap-2 border-b p-4 ${
          isHigh ? "bg-red-50 dark:bg-red-950/30" : ""
        }`}
      >
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Pipeline
          </div>
          <div className="font-mono text-lg font-semibold">
            {pipeline.pipeline_id}
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Badge className={levelBadgeClass(pipeline.risk_level)}>
              {pipeline.risk_level}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Risk score:{" "}
              <span className="font-semibold text-foreground">
                {pipeline.risk_score.toFixed(2)}
              </span>
            </span>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading details…
          </div>
        )}
        {error && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {detail && (
          <div>
            {isHigh && (
              <div className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                <div className="font-semibold">Estimated Failure Risk: HIGH</div>
                <div className="mt-1 text-xs">
                  Prototype ML estimate — recommend priority inspection.
                </div>
              </div>
            )}
            <Row label="Material" value={fmt(detail.material)} />
            <Row label="Pipe Age" value={fmt(detail.pipe_age, " yrs")} />
            <Row label="Diameter" value={fmt(detail.diameter, " mm")} />
            <Row label="Length" value={fmt(detail.length, " m")} />
            <Row label="Previous Failures" value={fmt(detail.previous_failures)} />
            <Row
              label="Days Since Maintenance"
              value={fmt(detail.days_since_last_maintenance)}
            />
            <Row
              label="Complaints (30d)"
              value={fmt(detail.complaints_last_30_days)}
            />
            <Row
              label="Leakage Complaints (30d)"
              value={fmt(detail.leakage_complaints_last_30_days)}
            />
            <Row label="Estimated Failure Risk" value={failureProb} />
          </div>
        )}
      </div>
    </div>
  );
}
