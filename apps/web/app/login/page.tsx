"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, UserRound, Users } from "lucide-react";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { login, me } from "@/lib/api/auth-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

const SHOW_DEMO_ACCOUNTS = process.env.NODE_ENV === "development";

export default function LoginPage() {
  const router = useRouter();
  const { refreshSession } = useSession();
  const [email, setEmail] = useState(SHOW_DEMO_ACCOUNTS ? "admin@example.com" : "");
  const [password, setPassword] = useState(SHOW_DEMO_ACCOUNTS ? "admin-pass" : "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      await refreshSession();
      router.replace("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center p-4 relative isolate">
      <div className="dashboard-grounding" />
      
      <div className="w-full max-w-md space-y-8 relative z-10">
        <div className="text-center space-y-2">
          <h1 className="text-h1 font-display tracking-tight text-foreground">Welcome Back</h1>
          <p className="text-sm text-muted-foreground font-medium">
            Sign in to your clinical workspace to manage your care plan.
          </p>
        </div>

        <div className="bg-surface border border-border-soft rounded-3xl p-8 shadow-lg shadow-black/[0.02]">
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="login-email" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">
                  Email Address
                </Label>
                <Input
                  id="login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="h-12 rounded-2xl bg-panel border-border-soft focus:ring-accent-teal/20 transition-all"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="login-password" title="Password" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">
                  Secure Password
                </Label>
                <Input
                  id="login-password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-12 rounded-2xl bg-panel border-border-soft focus:ring-accent-teal/20 transition-all"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-xl bg-rose-50 border border-rose-100 p-3 text-xs font-bold text-rose-600 animate-in fade-in slide-in-from-top-1">
                {error}
              </div>
            )}

            <Button
              className="w-full h-12 rounded-2xl font-bold shadow-lg shadow-accent-teal/20 bg-accent-teal hover:bg-accent-teal/90 text-white transition-all transform active:scale-[0.98]"
              onClick={handleLogin}
              disabled={loading || !email || !password}
            >
              {loading ? "Authenticating..." : "Sign In to Workspace"}
            </Button>

            <div className="pt-2 text-center">
              <p className="text-xs text-muted-foreground font-medium">
                Don&apos;t have an account?{" "}
                <Link href="/signup" className="text-accent-teal font-bold hover:underline">
                  Create Profile
                </Link>
              </p>
            </div>
          </div>
        </div>

        {SHOW_DEMO_ACCOUNTS && (
          <div className="space-y-4 pt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-border-soft" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase font-bold tracking-widest">
                <span className="bg-background px-4 text-muted-foreground">Sandbox Profiles</span>
              </div>
            </div>
            
            <div className="grid gap-2.5">
              {[
                { label: "Patient (Self)", email: "member@example.com", pass: "member-pass", icon: UserRound },
                { label: "Caregiver Role", email: "helper@example.com", pass: "helper-pass", icon: Users },
                { label: "System Admin", email: "admin@example.com", pass: "admin-pass", icon: ShieldCheck },
              ].map((acct) => {
                const Icon = acct.icon;
                return (
                  <button
                    key={acct.email}
                    className="flex items-center justify-between rounded-2xl border border-border-soft bg-surface/50 px-4 py-3 text-left transition-all hover:bg-surface hover:border-accent-teal/30 group"
                    onClick={() => {
                      setEmail(acct.email);
                      setPassword(acct.pass);
                    }}
                    type="button"
                  >
                    <span className="flex items-center gap-3 text-sm font-bold text-foreground">
                      <div className="h-8 w-8 rounded-xl bg-panel border border-border-soft flex items-center justify-center group-hover:bg-accent-teal/5 group-hover:border-accent-teal/20 transition-all">
                        <Icon className="h-4 w-4 text-muted-foreground group-hover:text-accent-teal transition-colors" />
                      </div>
                      {acct.label}
                    </span>
                    <span className="text-[10px] font-mono font-medium text-muted-foreground opacity-60">{acct.email}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
