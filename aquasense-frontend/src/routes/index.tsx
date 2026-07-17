import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Droplet,
  Gauge,
  FlaskConical,
  Waves,
  Wrench,
  MapPin,
  ClipboardList,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { SiteNav, SiteFooter } from "@/components/site-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/")({
  component: LandingPage,
});

const issueTypes = [
  { icon: Droplet, title: "Water Leakage", desc: "Visible leaks from pipes, valves, or hydrants." },
  { icon: Gauge, title: "Low Water Pressure", desc: "Weak flow or no water at the tap." },
  { icon: FlaskConical, title: "Discolored Water", desc: "Muddy, rusty, or unusually colored water." },
  { icon: Waves, title: "Unusual Water Flow", desc: "Sudden surges or reverse flow patterns." },
  { icon: Wrench, title: "Other Pipeline Issues", desc: "Anything else affecting your water supply." },
];

const steps = [
  { icon: ClipboardList, title: "Report the problem", desc: "Pick an issue type and describe what you're seeing." },
  { icon: MapPin, title: "Share the location", desc: "Use your current location or enter an address." },
  { icon: ShieldCheck, title: "Authorities receive it", desc: "Your report reaches the municipal water team." },
];

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteNav />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-hero">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background/80 px-3 py-1 text-xs font-medium text-brand shadow-soft">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              Citizen Reporting Portal
            </span>
            <h1 className="mt-5 text-4xl font-bold leading-tight text-foreground sm:text-5xl md:text-6xl">
              Report Water Problems.<br />
              <span className="text-brand">Help Prevent Bigger Failures.</span>
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Citizens can report leaks, low water pressure, unusual water flow and other
              pipeline problems in their area. Your reports help authorities detect water
              infrastructure issues earlier — before small problems become big ones.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95">
                <Link to="/report">
                  Report an Issue <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/track">Track Complaint</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">How it works</h2>
          <p className="mt-2 text-muted-foreground">Three simple steps, from your street to the control room.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {steps.map((s, i) => (
            <Card key={s.title} className="border-border/70 shadow-card">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                    <s.icon className="h-5 w-5" />
                  </span>
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Step {i + 1}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-foreground">{s.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{s.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Issue types */}
      <section className="border-t border-border/70 bg-secondary/40">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="mb-10 max-w-2xl">
            <h2 className="text-2xl font-bold text-foreground sm:text-3xl">What you can report</h2>
            <p className="mt-2 text-muted-foreground">
              Pick the option that best matches what you're seeing. You can add a photo and
              location when you file the report.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {issueTypes.map((t) => (
              <Card key={t.title} className="border-border/70 shadow-card transition-shadow hover:shadow-soft">
                <CardContent className="flex items-start gap-4 p-6">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand">
                    <t.icon className="h-5 w-5" />
                  </span>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-foreground">{t.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{t.desc}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="mt-10">
            <Button asChild size="lg" className="bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95">
              <Link to="/report">Start a report</Link>
            </Button>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
