import { createFileRoute, Link, Outlet, useRouterState, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { Droplets, LayoutDashboard, Map, MessagesSquare, ArrowLeft, LogOut, Loader2, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/authority")({
  component: AuthorityLayout,
});

const NAV = [
  { to: "/authority/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/authority/dashboard", label: "Pipeline Risk Map", icon: Map },
  { to: "/authority/complaints", label: "Citizen Complaints", icon: MessagesSquare },
] as const;

function AuthorityLayout() {
  const router = useRouter();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { authority, isAuthenticated, isLoading, logout } = useAuth();

  useEffect(() => {
    if (pathname !== "/authority/login" && !isLoading && !isAuthenticated) {
      router.navigate({ to: "/authority/login", replace: true });
    }
  }, [pathname, isLoading, isAuthenticated, router]);

  // Bypass portal layout for the login route
  if (pathname === "/authority/login") {
    return <Outlet />;
  }

  // Show loading state while session is being restored or redirecting
  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <a href="/" className="flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2 text-primary">
              <Droplets className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight">
                AQUA-SENSE Authority Portal
              </h1>
              <p className="text-xs text-muted-foreground">
                Indore water infrastructure & complaint management
              </p>
            </div>
          </a>
          <div className="flex items-center gap-3">
            {authority && (
              <div className="hidden items-center gap-2 rounded-md border bg-secondary/40 px-3 py-1.5 sm:flex">
                <User className="h-4 w-4 text-primary" />
                <div className="text-left leading-tight">
                  <div className="text-xs font-semibold text-foreground">{authority.name}</div>
                  <div className="text-[10px] text-muted-foreground">{authority.email}</div>
                </div>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="inline-flex items-center gap-1.5 text-xs font-medium"
            >
              <LogOut className="h-3.5 w-3.5" />
              Logout
            </Button>
            <a
              href="/"
              className="inline-flex items-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Citizen Portal
            </a>
            <Badge variant="outline" className="hidden sm:inline-flex">
              Prototype
            </Badge>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-2 pb-2">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                activeProps={{
                  className:
                    "bg-primary text-primary-foreground hover:bg-primary/90",
                }}
                inactiveProps={{
                  className:
                    "text-muted-foreground hover:bg-accent hover:text-foreground",
                }}
                className="inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
