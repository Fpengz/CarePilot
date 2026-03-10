"use client";

import Link from "next/link";
import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { signup } from "@/lib/api/auth-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

export default function SignupPage() {
  const { refreshSession } = useSession();
  const [displayName, setDisplayName] = useState("New Member");
  const [email, setEmail] = useState("newmember@example.com");
  const [password, setPassword] = useState("newmember-pass");
  const [profileMode, setProfileMode] = useState<"self" | "caregiver">("self");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <PageTitle
        eyebrow="Auth"
        title="Create Account"
        description="Email/password signup creates a member account and signs you in immediately."

      />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,560px)_minmax(0,1fr)]">
      <Card className="grain-overlay relative overflow-hidden">
        <CardHeader>
          <div className="mb-2 flex items-center gap-2">
            <Badge>Auth v2</Badge>
            <Badge variant="outline">signup</Badge>
          </div>
          <CardTitle className="text-2xl">Create Your Account</CardTitle>
          <CardDescription>
            Email/password signup creates a `member` account and starts a session immediately.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            <div className="space-y-2">
              <Label htmlFor="signup-display-name">Display name</Label>
              <Input
                id="signup-display-name"
                name="name"
                autoComplete="name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Alex Member"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="signup-email">Email</Label>
              <Input
                id="signup-email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="signup-password">Password</Label>
              <Input
                id="signup-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="signup-profile-mode">Usage mode</Label>
              <Select
                id="signup-profile-mode"
                value={profileMode}
                onChange={(e) => setProfileMode(e.target.value as "self" | "caregiver")}
              >
                <option value="self">For yourself</option>
                <option value="caregiver">Helping someone else</option>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={loading || !email || !password}
              onClick={async () => {
                setLoading(true);
                setError(null);
                try {
                  const data = await signup({
                    email,
                    password,
                    display_name: displayName,
                    profile_mode: profileMode,
                  });
                  setResult(data);
                  await refreshSession();
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoading(false);
                }
              }}
            >
              <AsyncLabel active={loading} idle="Create Account" loading="Creating" />
            </Button>
            <Button asChild variant="secondary">
              <Link href="/login">Go to Login</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {error ? <ErrorCard message={error} /> : null}
        {result ? (
          <JsonViewer
            title="Signup Response"
            description="Session is active after successful signup."
            data={result}
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Onboarding Note</CardTitle>
              <CardDescription>
                Household/group setup comes next in the v1 plan. This page covers account creation only.
              </CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
      </div>
    </div>
  );
}
