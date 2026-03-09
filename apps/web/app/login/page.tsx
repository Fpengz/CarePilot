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
  const [result, setResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [meResult, setMeResult] = useState<object | null>(null);

  return (
    <div>
      <PageTitle
        eyebrow="Auth"
        title="Sign In"
        description={
          SHOW_DEMO_ACCOUNTS
            ? "Use demo accounts to test session cookies, role/scopes, and the account panel flows."
            : "Sign in with your account to access the Dietary Guardian workspace."
        }
        tags={["cookie session", "account_role", "profile_mode"]}
      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,540px)_minmax(0,1fr)]">
      <Card className="grain-overlay relative overflow-hidden">
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <Badge>Auth v2</Badge>
            <Badge variant="outline">account_role + scopes</Badge>
          </div>
          <CardTitle className="text-2xl">{SHOW_DEMO_ACCOUNTS ? "Sign In to Demo Accounts" : "Sign In"}</CardTitle>
          <CardDescription>
            Backend-issued session cookie flow (`/api/v1/auth/login`).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-password">Password</Label>
              <Input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="admin-pass"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={async () => {
                setError(null);
                try {
                  const data = await login(email, password);
                  setResult(data);
                  await refreshSession();
                  router.replace("/dashboard");
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                }
              }}
            >
              Login
            </Button>
            <Button
              variant="secondary"
              onClick={async () => {
                setError(null);
                try {
                  const data = await me();
                  setMeResult(data);
                  await refreshSession();
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                }
              }}
            >
              Fetch /auth/me
            </Button>
            <Button asChild variant="secondary">
              <Link href="/signup">Go to Sign Up</Link>
            </Button>
          </div>
          {SHOW_DEMO_ACCOUNTS ? (
            <div className="grid gap-2 pt-2">
              {[
                { label: "Member (self)", email: "member@example.com", pass: "member-pass", icon: UserRound },
                { label: "Helper (member + caregiver mode)", email: "helper@example.com", pass: "helper-pass", icon: Users },
                { label: "Admin", email: "admin@example.com", pass: "admin-pass", icon: ShieldCheck },
              ].map((acct) => {
                const Icon = acct.icon;
                return (
                  <button
                    key={acct.email}
                    className="flex items-center justify-between rounded-xl border border-[color:var(--border)] bg-white/75 px-3 py-2 text-left text-[color:var(--foreground)] transition hover:bg-white dark:bg-[color:var(--panel-soft)] dark:hover:bg-[color:var(--card)]"
                    onClick={() => {
                      setEmail(acct.email);
                      setPassword(acct.pass);
                    }}
                    type="button"
                  >
                    <span className="flex items-center gap-2 text-sm font-medium">
                      <Icon className="h-4 w-4 text-[color:var(--accent)]" />
                      {acct.label}
                    </span>
                    <span className="text-xs text-[color:var(--muted-foreground)]">{acct.email}</span>
                  </button>
                );
              })}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {error ? (
          <ErrorCard message={error} />
        ) : null}
        {result ? <JsonViewer title="Login Response" data={result} /> : null}
        {meResult ? <JsonViewer title="Current Session (`/auth/me`)" data={meResult} /> : (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Foundation Applied</CardTitle>
              <CardDescription>
                Tailwind v4 + shadcn-style primitives are now wired in (`Button`, `Input`, `Card`, `Badge`).
              </CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
      </div>
    </div>
  );
}
