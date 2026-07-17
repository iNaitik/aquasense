import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getComplaints,
  getComplaintStats,
  ISSUE_TYPE_LABELS,
  STATUS_LABELS,
  type ComplaintStatus,
  type IssueType,
} from "@/lib/api/admin-complaints";
import { ComplaintDetailDialog } from "@/components/authority/ComplaintDetailDialog";

export const Route = createFileRoute("/authority/complaints")({
  head: () => ({
    meta: [
      { title: "Citizen Complaints — AQUA-SENSE Authority" },
      {
        name: "description",
        content: "Manage citizen water complaints for Indore.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ComplaintsPage,
});

type StatusFilter = ComplaintStatus | "all";
type IssueFilter = IssueType | "all";

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

function StatCard({
  label,
  value,
  accent,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  accent?: string;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className={`mt-2 text-2xl font-bold ${accent ?? ""}`}>
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : value}
        </div>
      </CardContent>
    </Card>
  );
}

const PAGE_SIZE = 20;

function ComplaintsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [issueFilter, setIssueFilter] = useState<IssueFilter>("all");
  const [page, setPage] = useState(1);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const statsQuery = useQuery({
    queryKey: ["admin-complaints", "stats"],
    queryFn: getComplaintStats,
    staleTime: 60_000,
  });

  const listQuery = useQuery({
    queryKey: [
      "admin-complaints",
      { page, statusFilter, issueFilter, pageSize: PAGE_SIZE },
    ],
    queryFn: () =>
      getComplaints({
        page,
        page_size: PAGE_SIZE,
        current_status: statusFilter,
        issue_type: issueFilter,
      }),
  });

  const s = statsQuery.data;
  const data = listQuery.data;
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;
  const startIdx = useMemo(
    () => (total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1),
    [page, total],
  );
  const endIdx = Math.min(page * PAGE_SIZE, total);

  const openDetail = (ref: string) => {
    setSelectedRef(ref);
    setDialogOpen(true);
  };

  const changeStatus = (v: StatusFilter) => {
    setStatusFilter(v);
    setPage(1);
  };
  const changeIssue = (v: IssueFilter) => {
    setIssueFilter(v);
    setPage(1);
  };

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4">
      {/* Stats */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard
          label="Total"
          value={s?.total_complaints ?? "—"}
          loading={statsQuery.isLoading}
        />
        <StatCard
          label="Submitted"
          value={s?.submitted ?? "—"}
          accent="text-blue-600"
          loading={statsQuery.isLoading}
        />
        <StatCard
          label="Reviewed"
          value={s?.reviewed ?? "—"}
          accent="text-purple-600"
          loading={statsQuery.isLoading}
        />
        <StatCard
          label="Assigned"
          value={s?.assigned ?? "—"}
          accent="text-amber-600"
          loading={statsQuery.isLoading}
        />
        <StatCard
          label="Resolved"
          value={s?.resolved ?? "—"}
          accent="text-green-600"
          loading={statsQuery.isLoading}
        />
      </section>

      {/* Filters */}
      <section className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Status
          </label>
          <Select
            value={statusFilter}
            onValueChange={(v) => changeStatus(v as StatusFilter)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="submitted">Submitted</SelectItem>
              <SelectItem value="reviewed">Reviewed</SelectItem>
              <SelectItem value="assigned">Assigned</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Issue Type
          </label>
          <Select
            value={issueFilter}
            onValueChange={(v) => changeIssue(v as IssueFilter)}
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Issues</SelectItem>
              <SelectItem value="water_leakage">Water Leakage</SelectItem>
              <SelectItem value="low_pressure">Low Water Pressure</SelectItem>
              <SelectItem value="discolored_water">Discolored Water</SelectItem>
              <SelectItem value="unusual_flow">Unusual Water Flow</SelectItem>
              <SelectItem value="other">Other Pipeline Issue</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="ml-auto text-sm text-muted-foreground">
          {total > 0
            ? `Showing ${startIdx}–${endIdx} of ${total} complaints`
            : ""}
        </div>
      </section>

      {/* Table */}
      <section className="rounded-lg border bg-card">
        {listQuery.isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
        {listQuery.isError && (
          <div className="p-8 text-center">
            <AlertTriangle className="mx-auto h-8 w-8 text-destructive" />
            <p className="mt-2 font-medium">Unable to load complaints.</p>
            <p className="text-sm text-muted-foreground">
              {(listQuery.error as Error)?.message}
            </p>
            <Button
              size="sm"
              className="mt-3"
              onClick={() => listQuery.refetch()}
            >
              Retry
            </Button>
          </div>
        )}
        {!listQuery.isLoading && !listQuery.isError && items.length === 0 && (
          <div className="p-10 text-center text-sm text-muted-foreground">
            No complaints found for the selected filters.
          </div>
        )}
        {!listQuery.isLoading && !listQuery.isError && items.length > 0 && (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Reference ID</TableHead>
                  <TableHead>Issue Type</TableHead>
                  <TableHead>Citizen</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((c) => (
                  <TableRow
                    key={c.reference_id}
                    className="cursor-pointer"
                    onClick={() => openDetail(c.reference_id)}
                  >
                    <TableCell className="font-mono text-xs font-semibold">
                      {c.reference_id}
                    </TableCell>
                    <TableCell>
                      {ISSUE_TYPE_LABELS[c.issue_type] ?? c.issue_type}
                    </TableCell>
                    <TableCell className="text-sm font-medium">
                      {c.citizen_name || "Not available"}
                    </TableCell>
                    <TableCell className="max-w-[220px] truncate text-sm text-muted-foreground">
                      {c.address ||
                        `${Number(c.latitude).toFixed(4)}, ${Number(c.longitude).toFixed(4)}`}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusBadgeClass(c.current_status)}>
                        {STATUS_LABELS[c.current_status]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(c.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          openDetail(c.reference_id);
                        }}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      {/* Pagination */}
      {total > 0 && (
        <section className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || listQuery.isFetching}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || listQuery.isFetching}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </section>
      )}

      <ComplaintDetailDialog
        referenceId={selectedRef}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </main>
  );
}
