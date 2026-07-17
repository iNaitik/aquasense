import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  Droplet,
  Gauge,
  FlaskConical,
  Waves,
  Wrench,
  Upload,
  MapPin,
  Loader2,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Copy,
  X,
} from "lucide-react";
import { SiteNav, SiteFooter } from "@/components/site-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  ISSUE_TYPE_LABELS,
  type ComplaintLocation,
  type IssueType,
} from "@/types/complaint";
import { complaintsApi } from "@/lib/api/complaints";

export const Route = createFileRoute("/report")({
  head: () => ({
    meta: [
      { title: "Report a Water Issue — AQUA-SENSE" },
      {
        name: "description",
        content:
          "Report a water pipeline problem in your area — leaks, low pressure, discolored water and more.",
      },
    ],
  }),
  component: ReportPage,
});

const ISSUE_OPTIONS: { value: IssueType; icon: typeof Droplet; desc: string }[] = [
  { value: "water_leakage", icon: Droplet, desc: "Visible leak from a pipe or valve" },
  { value: "low_pressure", icon: Gauge, desc: "Weak flow or no water at the tap" },
  { value: "discolored_water", icon: FlaskConical, desc: "Muddy, rusty or off-color water" },
  { value: "unusual_flow", icon: Waves, desc: "Sudden surges or reverse flow" },
  { value: "other", icon: Wrench, desc: "Other pipeline-related problem" },
];

type Step = 1 | 2 | 3 | 4;

function ReportPage() {
  const [step, setStep] = useState<Step>(1);
  const [issueType, setIssueType] = useState<IssueType | null>(null);
  const [citizenName, setCitizenName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [description, setDescription] = useState("");
  const [photo, setPhoto] = useState<{ file: File; preview: string } | null>(null);
  const [location, setLocation] = useState<ComplaintLocation>({
    latitude: null,
    longitude: null,
    address: "",
  });
  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [referenceId, setReferenceId] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handlePhoto(file: File | null) {
    if (photo) URL.revokeObjectURL(photo.preview);
    if (!file) return setPhoto(null);
    setPhoto({ file, preview: URL.createObjectURL(file) });
  }

  function useCurrentLocation() {
    if (!("geolocation" in navigator)) {
      toast.error("Geolocation not supported in this browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation((l) => ({
          ...l,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        }));
        setLocating(false);
        toast.success("Location captured.");
      },
      (err) => {
        setLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          toast.error("Location permission denied. You can enter an address instead.");
        } else {
          toast.error("Couldn't get your location. Try entering an address.");
        }
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  function validateStep(s: Step): boolean {
    const e: Record<string, string> = {};
    if (s === 1 && !issueType) e.issueType = "Please choose an issue type.";
    if (s === 2) {
      if (!citizenName.trim()) e.citizenName = "Please enter your full name.";
      if (!phoneNumber.trim()) {
        e.phoneNumber = "Please enter your mobile number.";
      } else if (phoneNumber.replace(/\D/g, "").length < 10) {
        e.phoneNumber = "Please enter at least a 10-digit mobile number.";
      }
      if (description.trim().length < 10)
        e.description = "Please describe the problem (at least 10 characters).";
    }
    if (s === 3 && !location.address.trim() && location.latitude == null)
      e.location = "Share your current location or enter an address.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function next() {
    if (validateStep(step)) setStep((s) => (s < 4 ? ((s + 1) as Step) : s));
  }
  function back() {
    setStep((s) => (s > 1 ? ((s - 1) as Step) : s));
  }

  async function submit() {
    if (!issueType) return;
    setSubmitting(true);
    try {
      const res = await complaintsApi.create({
        citizen_name: citizenName.trim(),
        phone_number: phoneNumber.trim(),
        issue_type: issueType,
        description: description.trim(),
        latitude: location.latitude,
        longitude: location.longitude,
        address: location.address.trim() || undefined,
        photo: photo?.file ?? null,
      });
      setReferenceId(res.reference_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      toast.error(`Couldn't submit: ${message}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (referenceId) {
    return <SuccessScreen referenceId={referenceId} />;
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteNav />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        <header className="mb-6">
          <h1 className="text-2xl font-bold sm:text-3xl">Report a water issue</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            It takes about a minute. Photos and location help crews respond faster.
          </p>
        </header>

        <Stepper current={step} />

        <Card className="mt-6 border-border/70 shadow-card">
          <CardContent className="p-5 sm:p-8">
            {step === 1 && (
              <div>
                <h2 className="text-lg font-semibold">What's the problem?</h2>
                <p className="mt-1 text-sm text-muted-foreground">Pick the closest match.</p>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {ISSUE_OPTIONS.map((opt) => {
                    const active = issueType === opt.value;
                    const Icon = opt.icon;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setIssueType(opt.value)}
                        className={cn(
                          "flex items-start gap-3 rounded-xl border p-4 text-left transition-all",
                          active
                            ? "border-brand bg-brand-soft ring-2 ring-brand/30"
                            : "border-border hover:border-brand/60 hover:bg-secondary/60",
                        )}
                      >
                        <span
                          className={cn(
                            "grid h-10 w-10 shrink-0 place-items-center rounded-lg",
                            active ? "bg-brand text-brand-foreground" : "bg-brand-soft text-brand",
                          )}
                        >
                          <Icon className="h-5 w-5" />
                        </span>
                        <span className="min-w-0">
                          <span className="block font-semibold">
                            {ISSUE_TYPE_LABELS[opt.value]}
                          </span>
                          <span className="mt-0.5 block text-sm text-muted-foreground">
                            {opt.desc}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
                {errors.issueType && (
                  <p className="mt-3 text-sm text-destructive">{errors.issueType}</p>
                )}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <div className="space-y-4 rounded-xl border border-border/80 bg-secondary/20 p-4 sm:p-5">
                  <div>
                    <h3 className="font-semibold text-foreground">Your Contact Information</h3>
                    <p className="text-xs text-muted-foreground">
                      Your mobile number will be used for complaint-related updates.
                    </p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="citizenName">Full Name</Label>
                      <Input
                        id="citizenName"
                        placeholder="e.g. Rahul Sharma"
                        value={citizenName}
                        onChange={(e) => setCitizenName(e.target.value)}
                        aria-invalid={!!errors.citizenName}
                      />
                      {errors.citizenName && (
                        <p className="text-sm text-destructive">{errors.citizenName}</p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phoneNumber">Mobile Number</Label>
                      <Input
                        id="phoneNumber"
                        type="tel"
                        placeholder="e.g. 9876543210"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        aria-invalid={!!errors.phoneNumber}
                      />
                      {errors.phoneNumber && (
                        <p className="text-sm text-destructive">{errors.phoneNumber}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div>
                  <h2 className="text-lg font-semibold">Describe the problem</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Include when it started, how bad it is, and anything else useful.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="desc">Description</Label>
                  <Textarea
                    id="desc"
                    rows={5}
                    placeholder="e.g. Water leaking continuously near the main road since last night, water logging on the pavement."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    aria-invalid={!!errors.description}
                  />
                  {errors.description && (
                    <p className="text-sm text-destructive">{errors.description}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>Photo (optional)</Label>
                  {photo ? (
                    <div className="relative overflow-hidden rounded-xl border border-border">
                      <img src={photo.preview} alt="Selected" className="max-h-72 w-full object-cover" />
                      <button
                        type="button"
                        onClick={() => handlePhoto(null)}
                        className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full bg-background/90 text-foreground shadow-soft"
                        aria-label="Remove photo"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-secondary/40 px-4 py-8 text-center text-sm text-muted-foreground hover:border-brand/60 hover:bg-brand-soft/40">
                      <Upload className="h-5 w-5 text-brand" />
                      <span className="font-medium text-foreground">Add a photo</span>
                      <span>PNG or JPG, up to a few MB</span>
                      <input
                        type="file"
                        accept="image/*"
                        className="sr-only"
                        onChange={(e) => handlePhoto(e.target.files?.[0] ?? null)}
                      />
                    </label>
                  )}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-semibold">Where is it?</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Use your current location, add an address, or both.
                  </p>
                </div>

                <Button
                  type="button"
                  onClick={useCurrentLocation}
                  disabled={locating}
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  {locating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <MapPin className="mr-2 h-4 w-4 text-brand" />
                  )}
                  Use My Current Location
                </Button>

                {location.latitude != null && location.longitude != null && (
                  <div className="rounded-lg border border-border bg-brand-soft/50 px-3 py-2 text-sm">
                    <span className="font-medium">Coordinates:</span>{" "}
                    {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="addr">Address / landmark</Label>
                  <Input
                    id="addr"
                    placeholder="e.g. Near Ward 12 community hall, MG Road"
                    value={location.address}
                    onChange={(e) => setLocation((l) => ({ ...l, address: e.target.value }))}
                  />
                </div>

                {errors.location && (
                  <p className="text-sm text-destructive">{errors.location}</p>
                )}
              </div>
            )}

            {step === 4 && issueType && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-semibold">Review & submit</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Double-check the details before sending it in.
                  </p>
                </div>

                <ReviewRow label="Full name" value={citizenName} />
                <ReviewRow label="Mobile number" value={phoneNumber} />
                <ReviewRow label="Issue type" value={ISSUE_TYPE_LABELS[issueType]} />
                <ReviewRow label="Description" value={description} />
                {photo && (
                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Photo
                    </p>
                    <img
                      src={photo.preview}
                      alt="Selected"
                      className="max-h-56 w-full rounded-lg border border-border object-cover"
                    />
                  </div>
                )}
                <ReviewRow
                  label="Location"
                  value={
                    [
                      location.address,
                      location.latitude != null && location.longitude != null
                        ? `(${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)})`
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" ") || "—"
                  }
                />
              </div>
            )}

            <div className="mt-8 flex items-center justify-between gap-3">
              <Button
                type="button"
                variant="ghost"
                onClick={back}
                disabled={step === 1 || submitting}
              >
                <ArrowLeft className="mr-1 h-4 w-4" /> Back
              </Button>
              {step < 4 ? (
                <Button
                  type="button"
                  onClick={next}
                  className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95"
                >
                  Continue <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={submit}
                  disabled={submitting}
                  className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95"
                >
                  {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Submit Complaint
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 border-b border-border/60 pb-3 last:border-none last:pb-0 sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-4">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground sm:pt-1">
        {label}
      </p>
      <p className="text-sm text-foreground whitespace-pre-wrap break-words">{value}</p>
    </div>
  );
}

function Stepper({ current }: { current: Step }) {
  const items = ["Issue", "Details", "Location", "Review"];
  return (
    <ol className="flex items-center gap-2">
      {items.map((label, i) => {
        const n = (i + 1) as Step;
        const active = n === current;
        const done = n < current;
        return (
          <li key={label} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-semibold transition-colors",
                done && "bg-brand text-brand-foreground",
                active && "bg-gradient-brand text-brand-foreground shadow-soft",
                !done && !active && "bg-secondary text-muted-foreground",
              )}
            >
              {done ? <CheckCircle2 className="h-4 w-4" /> : n}
            </div>
            <span
              className={cn(
                "hidden text-sm font-medium sm:inline",
                active ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {label}
            </span>
            {i < items.length - 1 && (
              <div className={cn("h-px flex-1", done ? "bg-brand" : "bg-border")} />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function SuccessScreen({ referenceId }: { referenceId: string }) {
  function copy() {
    navigator.clipboard.writeText(referenceId).then(() => toast.success("Reference copied."));
  }
  return (
    <div className="min-h-screen bg-background">
      <SiteNav />
      <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 sm:py-20">
        <Card className="border-border/70 shadow-card">
          <CardContent className="p-6 text-center sm:p-10">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-success/15 text-success">
              <CheckCircle2 className="h-7 w-7" />
            </div>
            <h1 className="mt-5 text-2xl font-bold sm:text-3xl">
              Complaint Submitted Successfully
            </h1>
            <p className="mt-2 text-muted-foreground">
              Thanks for reporting. Save this reference to track progress.
            </p>

            <div className="mx-auto mt-6 inline-flex items-center gap-2 rounded-xl border border-border bg-secondary/60 px-4 py-3 font-mono text-lg font-semibold tracking-wider">
              {referenceId}
              <button
                type="button"
                onClick={copy}
                className="rounded-md p-1 text-muted-foreground hover:text-foreground"
                aria-label="Copy reference"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95">
                <Link to="/track" search={{ ref: referenceId } as never}>
                  Track this complaint
                </Link>
              </Button>
              <Button asChild variant="outline">
                <a href="/">Back to home</a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
      <SiteFooter />
    </div>
  );
}
