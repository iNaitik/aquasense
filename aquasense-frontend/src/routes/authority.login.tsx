import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Droplets, Loader2, Lock, Mail, AlertCircle, ArrowLeft } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/authority/login")({
  head: () => ({
    meta: [
      { title: "Authority Sign In — AQUA-SENSE" },
      { name: "description", content: "Secure sign-in for municipal water authorities." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.navigate({ to: "/authority/overview", replace: true });
    }
  }, [isLoading, isAuthenticated, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please enter both email and password.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.navigate({ to: "/authority/overview", replace: true });
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  if (isLoading || isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b bg-card py-4 px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <a href="/" className="flex items-center gap-2.5">
            <div className="rounded-md bg-primary/10 p-2 text-primary">
              <Droplets className="h-5 w-5" />
            </div>
            <span className="font-display font-bold tracking-tight text-foreground">
              AQUA<span className="text-primary">-SENSE</span>
            </span>
          </a>
          <a
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Citizen Portal
          </a>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md border-border/70 shadow-card">
          <CardContent className="p-6 sm:p-8">
            <div className="text-center">
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary">
                <Lock className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                Authority Portal Sign In
              </h1>
              <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
                Enter your official credentials to access Indore pipeline risk maps and complaints.
              </p>
            </div>

            {error && (
              <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Official Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    required
                    placeholder="officer@aquasense.org"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9 font-mono text-sm"
                    disabled={submitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9"
                    disabled={submitting}
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={submitting}
                className="w-full bg-primary font-medium text-primary-foreground shadow-soft hover:bg-primary/90"
              >
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Sign In
              </Button>
            </form>

            <div className="mt-6 border-t border-border/60 pt-4 text-center text-xs text-muted-foreground">
              Authorized municipal officers only. Unauthorized access is strictly monitored.
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
