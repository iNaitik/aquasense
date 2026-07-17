import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Search, Loader2, CheckCircle2, Clock, MapPin, FileText, Image as ImageIcon } from "lucide-react";
import { SiteNav, SiteFooter } from "@/components/site-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/api/client";
import { complaintsApi } from "@/lib/api/complaints";
import { ISSUE_TYPE_LABELS, type ComplaintDetail } from "@/types/complaint";

type Search = { ref?: string };

export const Route = createFileRoute("/track")({
  head: () => ({
    meta: [
      { title: "Track a Complaint — AQUA-SENSE" },
      {
        name: "description",
        content: "Track the status of a water issue you reported using your complaint reference.",
      },
    ],
  }),
  validateSearch: (s: Record<string, unknown>): Search => ({
    ref: typeof s.ref === "string" ? s.ref : undefined,
  }),
  component: TrackPage,
});

function TrackPage() {
  const initial = Route.useSearch().ref ?? "";
  const [reference, setReference] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [complaint, setComplaint] = useState<ComplaintDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = reference.trim();
    if (!trimmed) {
      setError("Please enter a complaint reference.");
      return;
    }
    setLoading(true);
    setError(null);
    setComplaint(null);
    try {
      const data = await complaintsApi.getByReference(trimmed);
      setComplaint(data);
    } catch {
      setError("We couldn't find that complaint. Check the reference and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteNav />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl font-bold sm:text-3xl">Track your complaint</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter the reference number you received when you submitted the report.
          </p>
        </header>

        <Card className="border-border/70 shadow-card">
          <CardContent className="p-5 sm:p-6">
            <form onSubmit={submit} className="space-y-3">
              <Label htmlFor="ref">Complaint reference</Label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="ref"
                  placeholder="e.g. AQS-2026-0001"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  className="font-mono uppercase"
                  aria-invalid={!!error}
                />
                <Button
                  type="submit"
                  disabled={loading}
                  className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95"
                >
                  {loading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="mr-2 h-4 w-4" />
                  )}
                  Track
                </Button>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <p className="text-xs text-muted-foreground">
                Try a sample: <span className="font-mono">AQS-2026-0001</span>
              </p>
            </form>
          </CardContent>
        </Card>

        {complaint && (
          <section className="mt-6 space-y-4">
            <Card className="border-border/70 shadow-card">
              <CardContent className="p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Reference
                    </p>
                    <p className="font-mono text-lg font-semibold">{complaint.reference_id}</p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand">
                    {complaint.timeline.find((e) => e.status === complaint.current_status)?.label}
                  </span>
                </div>
                <div className="mt-4 grid gap-3 text-sm">
                  <Row icon={FileText} label="Issue">
                    {ISSUE_TYPE_LABELS[complaint.issue_type]}
                  </Row>
                  {complaint.address && (
                    <Row icon={MapPin} label="Location">
                      {complaint.address}
                    </Row>
                  )}
                </div>
                <p className="mt-4 rounded-lg border border-border bg-secondary/40 p-3 text-sm text-muted-foreground">
                  {complaint.description}
                </p>
                {complaint.image_url && (
                  <div className="mt-4">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      <ImageIcon className="h-3.5 w-3.5" /> Attached Photo
                    </p>
                    <a
                      href={
                        complaint.image_url.startsWith("/") &&
                        !complaint.image_url.startsWith("//")
                          ? `${API_BASE_URL}${complaint.image_url}`
                          : complaint.image_url
                      }
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group block overflow-hidden rounded-lg border border-border bg-secondary/20 transition hover:border-brand/50"
                    >
                      <img
                        src={
                          complaint.image_url.startsWith("/") &&
                          !complaint.image_url.startsWith("//")
                            ? `${API_BASE_URL}${complaint.image_url}`
                            : complaint.image_url
                        }
                        alt="Reported complaint attachment"
                        className="max-h-80 w-full object-cover object-center transition duration-300 group-hover:scale-[1.02]"
                      />
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-border/70 shadow-card">
              <CardContent className="p-5 sm:p-6">
                <h2 className="text-lg font-semibold">Progress</h2>
                <ol className="mt-4 space-y-4">
                  {complaint.timeline.map((event, i) => {
                    const done = !!event.timestamp;
                    const isCurrent = event.status === complaint.current_status;
                    return (
                      <li key={event.status} className="relative flex gap-4">
                        <div className="flex flex-col items-center">
                          <span
                            className={cn(
                              "grid h-8 w-8 place-items-center rounded-full border-2 transition-colors",
                              done
                                ? "border-brand bg-brand text-brand-foreground"
                                : "border-border bg-background text-muted-foreground",
                              isCurrent && !done && "border-brand text-brand",
                            )}
                          >
                            {done ? (
                              <CheckCircle2 className="h-4 w-4" />
                            ) : (
                              <Clock className="h-4 w-4" />
                            )}
                          </span>
                          {i < complaint.timeline.length - 1 && (
                            <span
                              className={cn(
                                "mt-1 h-full w-px flex-1",
                                done ? "bg-brand" : "bg-border",
                              )}
                            />
                          )}
                        </div>
                        <div className="pb-4">
                          <p
                            className={cn(
                              "font-medium",
                              done || isCurrent ? "text-foreground" : "text-muted-foreground",
                            )}
                          >
                            {event.label}
                          </p>
                          {event.timestamp && (
                            <p className="text-xs text-muted-foreground">
                              {new Date(event.timestamp).toLocaleString()}
                            </p>
                          )}
                          {event.note && (
                            <p className="mt-1 text-sm text-muted-foreground">{event.note}</p>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </CardContent>
            </Card>
          </section>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof MapPin;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <p className="text-foreground">{children}</p>
      </div>
    </div>
  );
}
