"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import {
  createHousehold,
  createHouseholdInvite,
  getCurrentHousehold,
  getHouseholdCareMemberDailySummary,
  getHouseholdCareMemberProfile,
  joinHousehold,
  leaveHousehold,
  listHouseholdCareMemberReminders,
  removeHouseholdMember,
  renameHousehold,
  setActiveHousehold,
} from "@/lib/api/household-client";
import type {
  HouseholdBundleApiResponse,
  HouseholdCareMealSummaryResponse,
  HouseholdCareProfileResponse,
  HouseholdCareReminderListResponse,
  HouseholdInvite,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

type ActionKey =
  | "load"
  | "create"
  | "rename"
  | "invite"
  | "join"
  | "leave"
  | "active"
  | "remove";

export default function HouseholdPage() {
  const { status, user } = useSession();
  const [bundle, setBundle] = useState<HouseholdBundleApiResponse | null>(null);
  const [lastInvite, setLastInvite] = useState<HouseholdInvite | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<ActionKey | null>(null);
  const [createName, setCreateName] = useState("My Household");
  const [renameValue, setRenameValue] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [removingUserId, setRemovingUserId] = useState<string | null>(null);
  const [selectedMemberUserId, setSelectedMemberUserId] = useState<string | null>(null);
  const [careProfile, setCareProfile] = useState<HouseholdCareProfileResponse | null>(null);
  const [careSummary, setCareSummary] = useState<HouseholdCareMealSummaryResponse | null>(null);
  const [careReminders, setCareReminders] = useState<HouseholdCareReminderListResponse | null>(null);

  const loadCurrent = useCallback(async () => {
    setBusy("load");
    setError(null);
    try {
      const current = await getCurrentHousehold();
      setBundle(current);
      setRenameValue(current.household?.name ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => {
    if (status === "authenticated") {
      void loadCurrent();
    }
  }, [status, loadCurrent]);

  const household = bundle?.household ?? null;
  const members = useMemo(() => bundle?.members ?? [], [bundle?.members]);
  const isOwner = Boolean(household && user && household.owner_user_id === user.user_id);
  const activeHouseholdId = bundle?.active_household_id ?? null;
  const canSetActive = Boolean(household);

  const ownerMember = useMemo(() => members.find((member) => member.role === "owner") ?? null, [members]);

  useEffect(() => {
    if (user?.profile_mode !== "caregiver" || !household) {
      setSelectedMemberUserId(null);
      setCareProfile(null);
      setCareSummary(null);
      setCareReminders(null);
      return;
    }
    if (members.length === 0) {
      setSelectedMemberUserId(null);
      return;
    }
    const currentMemberStillExists = selectedMemberUserId
      ? members.some((member) => member.user_id === selectedMemberUserId)
      : false;
    if (currentMemberStillExists) return;
    const preferred = members.find((member) => member.user_id !== user.user_id) ?? members[0];
    setSelectedMemberUserId(preferred.user_id);
  }, [household, members, selectedMemberUserId, user]);

  useEffect(() => {
    if (user?.profile_mode !== "caregiver" || !household || !selectedMemberUserId) return;
    let cancelled = false;
    const householdId = household.household_id;
    const memberUserId = selectedMemberUserId;
    async function loadCareView() {
      try {
        const [profile, summary, reminders] = await Promise.all([
          getHouseholdCareMemberProfile(householdId, memberUserId),
          getHouseholdCareMemberDailySummary(
            householdId,
            memberUserId,
            new Date().toISOString().slice(0, 10),
          ),
          listHouseholdCareMemberReminders(householdId, memberUserId),
        ]);
        if (cancelled) return;
        setCareProfile(profile);
        setCareSummary(summary);
        setCareReminders(reminders);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    }
    void loadCareView();
    return () => {
      cancelled = true;
    };
  }, [household, selectedMemberUserId, user]);

  async function withAction(action: ActionKey, fn: () => Promise<void>) {
    setBusy(action);
    setError(null);
    setNotice(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <PageTitle
        eyebrow="Household"
        title="Shared Wellness Group"
        description="Create a household, invite members, and manage a simple shared group (Apple-family-like basics for v1)."

      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Household Actions</CardTitle>
            <CardDescription>Create or join a household, then manage members and invites.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {status !== "authenticated" ? (
              <p className="app-muted text-sm">Sign in to manage household membership.</p>
            ) : null}

            <div className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="household-create-name">Create household</Label>
                <Input
                  id="household-create-name"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="My Household"
                />
                <Button
                  disabled={status !== "authenticated" || busy !== null || Boolean(household)}
                  onClick={() =>
                    withAction("create", async () => {
                      const next = await createHousehold(createName);
                      setBundle(next);
                      setRenameValue(next.household?.name ?? "");
                      setNotice("Household created.");
                    })
                  }
                >
                  <AsyncLabel active={busy === "create"} loading="Creating" idle="Create Household" />
                </Button>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label htmlFor="household-join-code">Join with invite code</Label>
                <Input
                  id="household-join-code"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value)}
                  placeholder="hh_abc123…"
                />
                <Button
                  variant="secondary"
                  disabled={status !== "authenticated" || busy !== null || !joinCode.trim() || Boolean(household)}
                  onClick={() =>
                    withAction("join", async () => {
                      const next = await joinHousehold(joinCode.trim());
                      setBundle(next);
                      setRenameValue(next.household?.name ?? "");
                      setNotice("Joined household.");
                    })
                  }
                >
                  <AsyncLabel active={busy === "join"} loading="Joining" idle="Join Household" />
                </Button>
              </div>

              {household ? (
                <>
                  <Separator />

                  <div className="space-y-2">
                    <Label htmlFor="household-rename">Rename household</Label>
                    <Input
                      id="household-rename"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      placeholder="Household name"
                      disabled={!isOwner}
                    />
                    <Button
                      disabled={busy !== null || !isOwner || !renameValue.trim() || renameValue.trim() === household.name}
                      onClick={() =>
                        withAction("rename", async () => {
                          const next = await renameHousehold(household.household_id, renameValue.trim());
                          setBundle(next);
                          setRenameValue(next.household?.name ?? "");
                          setNotice("Household renamed.");
                        })
                      }
                    >
                      <AsyncLabel active={busy === "rename"} loading="Saving" idle="Rename Household" />
                    </Button>
                  </div>

                  <div className="space-y-2">
                    <Label>Active household (session)</Label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={busy !== null || !canSetActive || activeHouseholdId === household.household_id}
                        onClick={() =>
                          withAction("active", async () => {
                            const result = await setActiveHousehold(household.household_id);
                            setBundle((prev) => (prev ? { ...prev, active_household_id: result.active_household_id } : prev));
                            setNotice("Active household set for this session.");
                          })
                        }
                      >
                        <AsyncLabel active={busy === "active"} loading="Saving" idle="Set Active" />
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={busy !== null || activeHouseholdId == null}
                        onClick={() =>
                          withAction("active", async () => {
                            const result = await setActiveHousehold(null);
                            setBundle((prev) => (prev ? { ...prev, active_household_id: result.active_household_id } : prev));
                            setNotice("Cleared active household for this session.");
                          })
                        }
                      >
                        Clear Active
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Invites</Label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={busy !== null || !isOwner}
                        onClick={() =>
                          withAction("invite", async () => {
                            const response = await createHouseholdInvite(household.household_id);
                            setLastInvite(response.invite);
                            setNotice("Invite created.");
                          })
                        }
                      >
                        <AsyncLabel active={busy === "invite"} loading="Creating" idle="Create Invite Code" />
                      </Button>
                    </div>
                    {lastInvite ? (
                      <div className="metric-card">
                        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                          Latest Invite
                        </div>
                        <div className="mt-1 break-all text-sm font-medium">{lastInvite.code}</div>
                        <div className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                          Expires {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(lastInvite.expires_at))}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="space-y-2">
                    <Label>Membership</Label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="ghost"
                        disabled={busy !== null}
                        onClick={() => void loadCurrent()}
                      >
                        <AsyncLabel active={busy === "load"} loading="Refreshing" idle="Refresh Household" />
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={busy !== null || !household || isOwner}
                        onClick={() =>
                          withAction("leave", async () => {
                            await leaveHousehold(household.household_id);
                            const next = await getCurrentHousehold();
                            setBundle(next);
                            setLastInvite(null);
                            setRenameValue(next.household?.name ?? "");
                            setNotice("Left household.");
                          })
                        }
                      >
                        <AsyncLabel active={busy === "leave"} loading="Leaving" idle="Leave Household" />
                      </Button>
                    </div>
                    {!isOwner && household ? (
                      <p className="app-muted text-xs">Owners cannot leave in v1. Ownership transfer/disband is a later milestone.</p>
                    ) : null}
                  </div>
                </>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          {notice ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm">{notice}</p>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Current Household</CardTitle>
              <CardDescription>Session-aware household view with member list and owner actions.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {household ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Name</div>
                      <div className="mt-1 text-sm font-medium">{household.name}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Active (Session)</div>
                      <div className="mt-1 text-sm font-medium">
                        {activeHouseholdId === household.household_id ? "Yes" : "No"}
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Owner</div>
                      <div className="mt-1 text-sm font-medium">{ownerMember?.display_name ?? household.owner_user_id}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Members</div>
                      <div className="mt-1 text-sm font-medium">{members.length}</div>
                    </div>
                  </div>

                  <Separator />
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Member List</div>
                    <div className="space-y-2">
                      {members.map((member) => {
                        const canRemove = isOwner && member.role !== "owner";
                        const isSelf = user?.user_id === member.user_id;
                        return (
                          <div
                            key={member.user_id}
                            className="flex flex-col gap-2 rounded-xl border border-[color:var(--border)] bg-white/60 px-3 py-3 dark:bg-[color:var(--panel-soft)] sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="truncate text-sm font-medium">{member.display_name}</span>
                                <Badge variant={member.role === "owner" ? "default" : "outline"}>{member.role}</Badge>
                                {isSelf ? <Badge variant="outline">You</Badge> : null}
                              </div>
                              <div className="mt-1 text-xs text-[color:var(--muted-foreground)]">{member.user_id}</div>
                            </div>
                            {canRemove ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy !== null}
                                onClick={() =>
                                  withAction("remove", async () => {
                                    setRemovingUserId(member.user_id);
                                    try {
                                      await removeHouseholdMember(household.household_id, member.user_id);
                                      const next = await getCurrentHousehold();
                                      setBundle(next);
                                      setNotice(`Removed ${member.display_name}.`);
                                    } finally {
                                      setRemovingUserId(null);
                                    }
                                  })
                                }
                              >
                                <AsyncLabel
                                  active={busy === "remove" && removingUserId === member.user_id}
                                  loading="Removing"
                                  idle="Remove"
                                />
                              </Button>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              ) : (
                <p className="app-muted text-sm">
                  You are not in a household yet. Create one or join with an invite code.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Caregiving View</CardTitle>
              <CardDescription>Read-only monitoring for the selected household member.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {user?.profile_mode !== "caregiver" ? (
                <p className="app-muted text-sm">
                  Switch your account mode to caregiver in Settings to unlock read-only household monitoring.
                </p>
              ) : null}

              {user?.profile_mode === "caregiver" && !household ? (
                <p className="app-muted text-sm">
                  Create or join a household first. The caregiving panel uses the active household membership only.
                </p>
              ) : null}

              {user?.profile_mode === "caregiver" && household ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="care-member-select">Selected member</Label>
                    <Select
                      id="care-member-select"
                      value={selectedMemberUserId ?? ""}
                      onChange={(event) => setSelectedMemberUserId(event.target.value)}
                    >
                      {members.map((member) => (
                        <option key={member.user_id} value={member.user_id}>
                          {member.display_name}
                        </option>
                      ))}
                    </Select>
                    <p className="app-muted text-xs">
                      {selectedMemberUserId === user.user_id
                        ? "Viewing your own profile."
                        : "Viewing another household member in read-only mode."}
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Profile state</div>
                      <div className="mt-1 text-sm font-medium">
                        {careProfile?.profile.completeness.state ?? "Loading"}
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meals logged today</div>
                      <div className="mt-1 text-sm font-medium">{careSummary?.summary.meal_count ?? 0}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining protein</div>
                      <div className="mt-1 text-sm font-medium">
                        {Math.round(careSummary?.summary.remaining.protein_g ?? 0)} g
                      </div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Pending reminders</div>
                      <div className="mt-1 text-sm font-medium">{careReminders?.reminders.length ?? 0}</div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium">Recent insight summary</div>
                    {careSummary?.summary.insights.length ? (
                      careSummary.summary.insights.slice(0, 2).map((insight) => (
                        <div
                          key={insight.code}
                          className="rounded-xl border border-[color:var(--border)] bg-white/60 px-3 py-3 dark:bg-[color:var(--panel-soft)]"
                        >
                          <div className="text-sm font-medium">{insight.title}</div>
                          <div className="app-muted mt-1 text-sm">{insight.summary}</div>
                        </div>
                      ))
                    ) : (
                      <p className="app-muted text-sm">No pattern-level insights yet for the selected member.</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium">Reminder preview</div>
                    {careReminders?.reminders.length ? (
                      careReminders.reminders.slice(0, 3).map((reminder) => (
                        <div
                          key={reminder.id}
                          className="rounded-xl border border-[color:var(--border)] bg-white/60 px-3 py-3 dark:bg-[color:var(--panel-soft)]"
                        >
                          <div className="text-sm font-medium">{reminder.title}</div>
                          <div className="app-muted mt-1 text-xs">
                            {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
                              new Date(reminder.scheduled_at),
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="app-muted text-sm">No reminders found for the selected member.</p>
                    )}
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
