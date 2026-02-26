"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { KeyRound, Loader2, LogOut, RefreshCw, Shield, User, X } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { useDialogA11y } from "@/components/app/use-dialog-a11y";
import {
  listAuthAuditEvents,
  listAuthSessions,
  logout,
  revokeAuthSession,
  revokeOtherAuthSessions,
  updateAuthPassword,
  updateAuthProfile,
} from "@/lib/api";
import type { AuthAuditEvent, AuthSessionListItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

function formatIssuedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function AccountPanel() {
  const { status, user, refreshSession } = useSession();
  const [open, setOpen] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [panelNotice, setPanelNotice] = useState<string | null>(null);
  const [sessions, setSessions] = useState<AuthSessionListItem[] | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuthAuditEvent[] | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [revokingOthers, setRevokingOthers] = useState(false);
  const [revokingSessionId, setRevokingSessionId] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  const [displayNameInput, setDisplayNameInput] = useState("");
  const [profileModeInput, setProfileModeInput] = useState<"self" | "caregiver">("self");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const panelId = useId();

  useDialogA11y({
    open,
    containerRef: panelRef,
    initialFocusRef: closeButtonRef,
    returnFocusRef: triggerRef,
    onClose: () => setOpen(false),
  });

  useEffect(() => {
    if (!user) return;
    setDisplayNameInput(user.display_name);
    setProfileModeInput(user.profile_mode);
  }, [user]);

  const loadSessions = useCallback(async () => {
    if (!user) return;
    setSessionsLoading(true);
    setPanelError(null);
    try {
      const data = await listAuthSessions();
      setSessions(data.sessions);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setSessionsLoading(false);
    }
  }, [user]);

  const loadAuditEvents = useCallback(async () => {
    if (!user || !user.scopes.includes("auth:audit:read")) return;
    setAuditLoading(true);
    setPanelError(null);
    try {
      const data = await listAuthAuditEvents(20);
      setAuditEvents(data.items);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setAuditLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!open || !user) return;
    void loadSessions();
    if (user.scopes.includes("auth:audit:read")) {
      void loadAuditEvents();
    }
  }, [open, user, loadSessions, loadAuditEvents]);

  const canManage = status === "authenticated" && Boolean(user);
  const hasProfileChanges =
    !!user && (displayNameInput !== user.display_name || profileModeInput !== user.profile_mode);

  const titleChip = useMemo(() => {
    if (!user) return null;
    const Icon = user.account_role === "admin" ? Shield : User;
    return (
      <Badge className="gap-1.5">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {user.account_role}
      </Badge>
    );
  }, [user]);

  async function handleSaveProfile() {
    if (!user) return;
    setSavingProfile(true);
    setPanelError(null);
    setPanelNotice(null);
    try {
      const payload: { display_name?: string; profile_mode?: "self" | "caregiver" } = {};
      if (displayNameInput !== user.display_name) payload.display_name = displayNameInput;
      if (profileModeInput !== user.profile_mode) payload.profile_mode = profileModeInput;
      await updateAuthProfile(payload);
      await refreshSession();
      setPanelNotice("Profile updated.");
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleChangePassword() {
    setSavingPassword(true);
    setPanelError(null);
    setPanelNotice(null);
    try {
      const result = await updateAuthPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      await loadSessions();
      setPanelNotice(
        result.revoked_other_sessions > 0
          ? `Password updated. Revoked ${result.revoked_other_sessions} other session(s).`
          : "Password updated.",
      );
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleRevokeOthers() {
    setRevokingOthers(true);
    setPanelError(null);
    setPanelNotice(null);
    try {
      const result = await revokeOtherAuthSessions();
      await loadSessions();
      setPanelNotice(
        result.revoked_count > 0
          ? `Revoked ${result.revoked_count} other session(s).`
          : "No other sessions to revoke.",
      );
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setRevokingOthers(false);
    }
  }

  async function handleRevokeSession(sessionId: string) {
    const isCurrent = sessions?.some((item) => item.session_id === sessionId && item.is_current) ?? false;
    setRevokingSessionId(sessionId);
    setPanelError(null);
    setPanelNotice(null);
    try {
      const result = await revokeAuthSession(sessionId);
      if (result.revoked) {
        await refreshSession();
      }
      if (isCurrent) {
        setOpen(false);
        return;
      }
      await loadSessions();
      setPanelNotice(result.revoked ? "Session revoked." : "Session was already gone.");
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setRevokingSessionId(null);
    }
  }

  async function handleLogout() {
    setLoggingOut(true);
    setPanelError(null);
    setPanelNotice(null);
    try {
      await logout();
      await refreshSession();
      setOpen(false);
    } catch (err) {
      setPanelError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        className="gap-2"
      >
        {titleChip}
        <span className="max-w-[10rem] truncate">
          {user ? user.display_name : status === "loading" ? "Session…" : "Account"}
        </span>
      </Button>

      {open ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 bg-black/40 backdrop-blur-[1px]"
            aria-label="Close account panel"
            onClick={() => setOpen(false)}
          />
          <div
            ref={panelRef}
            id={panelId}
            role="dialog"
            aria-modal="true"
            aria-label="Account settings"
            className="absolute right-0 top-0 h-full w-full max-w-xl border-l border-[color:var(--border)] bg-[color:var(--background)] p-4 shadow-2xl sm:p-5"
          >
            <div className="flex h-full flex-col gap-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <h3 className="text-lg font-semibold">Account</h3>
                    {titleChip}
                    {user ? <Badge variant="outline">{user.profile_mode}</Badge> : null}
                  </div>
                  <p className="text-sm text-[color:var(--muted-foreground)]">
                    {user ? user.email : "Sign in to manage profile, password, and sessions."}
                  </p>
                </div>
                <Button
                  ref={closeButtonRef}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setOpen(false)}
                  className="px-2.5"
                >
                  <X className="h-4 w-4" aria-hidden />
                  <span className="sr-only">Close</span>
                </Button>
              </div>

              {panelError ? <ErrorCard message={panelError} /> : null}
              {panelNotice ? (
                <Card className="border-emerald-300/70 bg-emerald-50/70 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Updated</CardTitle>
                    <CardDescription className="text-emerald-900/85 dark:text-emerald-200">
                      {panelNotice}
                    </CardDescription>
                  </CardHeader>
                </Card>
              ) : null}

              {!canManage ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Sign in required</CardTitle>
                    <CardDescription>
                      This panel uses the live auth session. Sign in on the Login page first.
                    </CardDescription>
                  </CardHeader>
                </Card>
              ) : (
                <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto pr-1">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Profile</CardTitle>
                      <CardDescription>Update display name and current usage mode.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="space-y-2">
                        <Label htmlFor="account-display-name">Display name</Label>
                        <Input
                          id="account-display-name"
                          value={displayNameInput}
                          onChange={(event) => setDisplayNameInput(event.target.value)}
                          autoComplete="name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="account-profile-mode">Usage mode</Label>
                        <Select
                          id="account-profile-mode"
                          value={profileModeInput}
                          onChange={(event) =>
                            setProfileModeInput(event.target.value as "self" | "caregiver")
                          }
                        >
                          <option value="self">For yourself</option>
                          <option value="caregiver">Helping someone else</option>
                        </Select>
                      </div>
                      <Button
                        type="button"
                        onClick={handleSaveProfile}
                        disabled={savingProfile || !hasProfileChanges}
                      >
                        <AsyncLabel active={savingProfile} idle="Save Profile" loading="Saving" />
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Password</CardTitle>
                      <CardDescription>
                        Change your password and revoke other active sessions.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="space-y-2">
                        <Label htmlFor="current-password">Current password</Label>
                        <Input
                          id="current-password"
                          type="password"
                          autoComplete="current-password"
                          value={currentPassword}
                          onChange={(event) => setCurrentPassword(event.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="new-password">New password</Label>
                        <Input
                          id="new-password"
                          type="password"
                          autoComplete="new-password"
                          value={newPassword}
                          onChange={(event) => setNewPassword(event.target.value)}
                        />
                      </div>
                      <Button
                        type="button"
                        onClick={handleChangePassword}
                        disabled={savingPassword || !currentPassword || !newPassword}
                        className="gap-2"
                      >
                        <KeyRound className="h-4 w-4" aria-hidden />
                        <AsyncLabel active={savingPassword} idle="Change Password" loading="Updating" />
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Sessions</CardTitle>
                      <CardDescription>Review active sessions and revoke access if needed.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => void loadSessions()}
                          disabled={sessionsLoading}
                          className="gap-2"
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${sessionsLoading ? "animate-spin" : ""}`}
                            aria-hidden
                          />
                          Refresh
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={handleRevokeOthers}
                          disabled={revokingOthers}
                        >
                          <AsyncLabel active={revokingOthers} idle="Revoke Others" loading="Revoking" />
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={handleLogout}
                          disabled={loggingOut}
                          className="gap-2"
                        >
                          {loggingOut ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <LogOut className="h-4 w-4" aria-hidden />}
                          <AsyncLabel active={loggingOut} idle="Logout" loading="Logging Out" />
                        </Button>
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        {sessionsLoading && !sessions ? (
                          <div className="text-sm text-[color:var(--muted-foreground)]">Loading sessions…</div>
                        ) : null}
                        {sessions && sessions.length === 0 ? (
                          <div className="text-sm text-[color:var(--muted-foreground)]">No active sessions.</div>
                        ) : null}
                        {sessions?.map((item) => (
                          <div
                            key={item.session_id}
                            className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel-soft)] p-3"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="mb-1 flex flex-wrap items-center gap-2">
                                  <Badge variant={item.is_current ? "default" : "outline"}>
                                    {item.is_current ? "Current" : "Session"}
                                  </Badge>
                                  <code className="max-w-[18rem] truncate text-xs text-[color:var(--muted-foreground)]">
                                    {item.session_id}
                                  </code>
                                </div>
                                <div className="text-sm text-[color:var(--muted-foreground)]">
                                  Started {formatIssuedAt(item.issued_at)}
                                </div>
                              </div>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                disabled={revokingSessionId === item.session_id}
                                onClick={() => void handleRevokeSession(item.session_id)}
                              >
                                <AsyncLabel
                                  active={revokingSessionId === item.session_id}
                                  idle={item.is_current ? "Sign Out This Session" : "Revoke"}
                                  loading="Revoking"
                                />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {user?.scopes.includes("auth:audit:read") ? (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Auth Audit</CardTitle>
                        <CardDescription>
                          Recent authentication security events (admin access only).
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => void loadAuditEvents()}
                            disabled={auditLoading}
                            className="gap-2"
                          >
                            <RefreshCw
                              className={`h-4 w-4 ${auditLoading ? "animate-spin" : ""}`}
                              aria-hidden
                            />
                            Refresh Audit
                          </Button>
                        </div>
                        <Separator />
                        <div className="space-y-2">
                          {auditLoading && !auditEvents ? (
                            <div className="text-sm text-[color:var(--muted-foreground)]">
                              Loading audit events…
                            </div>
                          ) : null}
                          {auditEvents && auditEvents.length === 0 ? (
                            <div className="text-sm text-[color:var(--muted-foreground)]">
                              No audit events yet.
                            </div>
                          ) : null}
                          {auditEvents?.map((event) => (
                            <div
                              key={event.event_id}
                              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel-soft)] p-3"
                            >
                              <div className="mb-1 flex flex-wrap items-center gap-2">
                                <Badge variant="outline">{event.event_type}</Badge>
                                <span className="text-xs text-[color:var(--muted-foreground)]">
                                  {formatIssuedAt(event.created_at)}
                                </span>
                              </div>
                              <div className="text-sm font-medium">{event.email}</div>
                              {Object.keys(event.metadata ?? {}).length > 0 ? (
                                <pre className="mt-2 overflow-x-auto rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] p-2 text-xs text-[color:var(--muted-foreground)]">
                                  {JSON.stringify(event.metadata, null, 2)}
                                </pre>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
