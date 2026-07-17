import { Link } from "@tanstack/react-router";
import { Droplets, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const links = [
  { to: "/", label: "Home" },
  { to: "/report", label: "Report Issue" },
  { to: "/track", label: "Track Complaint" },
  { to: "/authority/overview", label: "Authority Portal" },
] as const;

export function SiteNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-brand text-brand-foreground shadow-soft">
            <Droplets className="h-5 w-5" />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">
            AQUA<span className="text-brand">-SENSE</span>
          </span>
        </a>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              activeProps={{ className: "text-brand" }}
              inactiveProps={{ className: "text-muted-foreground hover:text-foreground" }}
              className="rounded-md px-3 py-2 text-sm font-medium transition-colors"
            >
              {l.label}
            </Link>
          ))}
          <Button asChild size="sm" className="ml-2 bg-gradient-brand text-brand-foreground shadow-soft hover:opacity-95">
            <Link to="/report">Report an Issue</Link>
          </Button>
        </nav>

        <button
          type="button"
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-2 text-foreground md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border md:hidden">
          <nav className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
            {links.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                activeOptions={{ exact: l.to === "/" }}
                activeProps={{ className: "bg-brand-soft text-brand" }}
                className="rounded-md px-3 py-2 text-sm font-medium text-foreground"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-border/70 bg-background">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6">
        <p>© {new Date().getFullYear()} AQUA-SENSE · Citizen Reporting Portal</p>
        <p>Built for municipal water infrastructure teams.</p>
      </div>
    </footer>
  );
}
