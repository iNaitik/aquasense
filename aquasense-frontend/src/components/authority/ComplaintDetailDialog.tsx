import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, ExternalLink, Loader2, MapPin } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  getComplaintByReference,
  updateComplaintStatus,
  nextStatus,
  nextStatusLabel,
  ISSUE_TYPE_LABELS,
  STATUS_LABELS,
  STATUS_ORDER,
  type ComplaintStatus,
  type ComplaintStatusEvent,
} from "@/lib/api/admin-complaints";
import { API_BASE_URL } from "@/lib/api/client";

function statusBadgeClass(s: ComplaintStatus) {
  switch (s) {
    case "submitted":
      return "bg-blue-600 text-white hover:bg-blue-600";
    case "reviewed":
      return "bg-purple-600 text-white hover:bg-purple-600";
    case "assigned":
      return "bg-amber-500 text-white hover:bg-amber-500";
    case "resolved":
      return "bg-green-600 text-white hover:bg-green-600";
  }
}

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function ComplaintDetailDialog({
  referenceId,
  open,
  onOpenChange,
}: {
  referenceId: string | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["admin-complaint", referenceId],
    queryFn: () => getComplaintByReference(referenceId as string),
    enabled: !!referenceId && open,
  });

  const mutation = useMutation({
    mutationFn: (status: ComplaintStatus) =>
      updateComplaintStatus(referenceId as string, status),
    onSuccess: () => {
      toast.success("Complaint status updated");
      qc.invalidateQueries({ queryKey: ["admin-complaint", referenceId] });
      qc.invalidateQueries({ queryKey: ["admin-complaints"] });
      qc.invalidateQueries({ queryKey: ["admin-complaints", "stats"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to update status");
    },
  });

  const complaint = query.data;
  const timeline: ComplaintStatusEvent[] =
    complaint?.timeline ?? complaint?.status_timeline ?? complaint?.status_history ?? [];
  const timelineMap = new Map<ComplaintStatus, string | null>();
  for (const ev of timeline) timelineMap.set(ev.status, ev.timestamp);
  // Fallback: created_at → submitted
  if (complaint?.created_at && !timelineMap.has("submitted")) {
    timelineMap.set("submitted", complaint.created_at);
  }

  const next = complaint ? nextStatus(complaint.current_status) : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-base">
            {referenceId ?? "Complaint"}
          </DialogTitle>
          <DialogDescription>Complaint details and status management</DialogDescription>
        </DialogHeader>

        {query.isLoading && (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {query.isError && (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm">
            <div className="font-medium text-destructive">
              Unable to load complaint
            </div>
            <p className="mt-1 text-muted-foreground">
              {(query.error as Error)?.message || "Please try again."}
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-3"
              onClick={() => query.refetch()}
            >
              Retry
            </Button>
          </div>
        )}

        {complaint && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={statusBadgeClass(complaint.current_status)}>
                {STATUS_LABELS[complaint.current_status]}
              </Badge>
              <Badge variant="outline">
                {ISSUE_TYPE_LABELS[complaint.issue_type] ?? complaint.issue_type}
              </Badge>
            </div>

            {complaint.image_url && (
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                  Attached Photo
                </div>
                <div className="overflow-hidden rounded-md border max-h-64 bg-muted flex items-center justify-center">
                  <img
                    src={
                      complaint.image_url.startsWith("http")
                        ? complaint.image_url
                        : `${API_BASE_URL}${complaint.image_url}`
                    }
                    alt="Complaint photo"
                    className="max-h-64 w-full object-contain"
                  />
                </div>
              </div>
            )}

            <div>
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Description
              </div>
              <p className="mt-1 text-sm">{complaint.description}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Citizen Name
                </div>
                <p className="mt-1 text-sm font-medium">{complaint.citizen_name || "Not available"}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Mobile Number
                </div>
                <p className="mt-1 text-sm font-mono">{complaint.phone_number || "Not available"}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Address
                </div>
                <p className="mt-1 text-sm">{complaint.address || "—"}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Location
                </div>
                {complaint.latitude != null && complaint.longitude != null ? (
                  <p className="mt-1 flex items-center gap-1 text-sm">
                    <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                    {Number(complaint.latitude).toFixed(5)}, {Number(complaint.longitude).toFixed(5)}
                    <a
                      href={`https://www.openstreetmap.org/?mlat=${complaint.latitude}&mlon=${complaint.longitude}#map=17/${complaint.latitude}/${complaint.longitude}`}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-1 text-primary hover:underline"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </p>
                ) : (
                  <p className="mt-1 text-sm">—</p>
                )}
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Created
                </div>
                <p className="mt-1 text-sm">{formatDate(complaint.created_at)}</p>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Last updated
                </div>
                <p className="mt-1 text-sm">{formatDate(complaint.updated_at)}</p>
              </div>
            </div>

            <Separator />

            <div>
              <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                Status Timeline
              </div>
              <ol className="space-y-3">
                {STATUS_ORDER.map((s, idx) => {
                  const reached =
                    STATUS_ORDER.indexOf(complaint.current_status) >= idx;
                  const ts = timelineMap.get(s);
                  return (
                    <li key={s} className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                          reached
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {reached ? <Check className="h-3.5 w-3.5" /> : idx + 1}
                      </span>
                      <div className="flex-1">
                        <div
                          className={`text-sm font-medium ${reached ? "" : "text-muted-foreground"}`}
                        >
                          {STATUS_LABELS[s]}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {ts ? formatDate(ts) : reached ? "—" : "Pending"}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>

            <Separator />

            <div className="flex justify-end">
              {next ? (
                <Button
                  onClick={() => mutation.mutate(next)}
                  disabled={mutation.isPending}
                >
                  {mutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {nextStatusLabel(complaint.current_status)}
                </Button>
              ) : (
                <Button disabled variant="secondary">
                  <Check className="mr-2 h-4 w-4" /> Resolved
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
