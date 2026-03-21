"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

export default function HouseholdPage() {
  const { status, user } = useSession();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  
  const [createName, setCreateName] = useState("My Household");
  const [renameValue, setRenameValue] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [selectedMemberUserId, setSelectedMemberUserId] = useState<string | null>(null);

  // Main bundle query
  const { data: bundle, isLoading: bundleLoading } = useQuery({
    queryKey: ["household-bundle"],
    queryFn: getCurrentHousehold,
    enabled: status === "authenticated",
  });

  const household = bundle?.household ?? null;
  const members = useMemo(() => bundle?.members ?? [], [bundle?.members]);
  const isOwner = Boolean(household && user && household.owner_user_id === user.user_id);
  const activeHouseholdId = bundle?.active_household_id ?? null;
  const canSetActive = Boolean(household);
  const ownerMember = useMemo(() => members.find((m) => m.role === "owner") ?? null, [members]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: createHousehold,
    onSuccess: (next) => {
      queryClient.setQueryData(["household-bundle"], next);
      setRenameValue(next.household?.name ?? "");
      setNotice("Household created.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const joinMutation = useMutation({
    mutationFn: joinHousehold,
    onSuccess: (next) => {
      queryClient.setQueryData(["household-bundle"], next);
      setRenameValue(next.household?.name ?? "");
      setNotice("Joined household.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const renameMutation = useMutation({
    mutationFn: (name: string) => renameHousehold(household!.household_id, name),
    onSuccess: (next) => {
      queryClient.setQueryData(["household-bundle"], next);
      setNotice("Household renamed.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const setActiveMutation = useMutation({
    mutationFn: setActiveHousehold,
    onSuccess: (result) => {
      queryClient.setQueryData(["household-bundle"], (prev: any) => 
        prev ? { ...prev, active_household_id: result.active_household_id } : prev
      );
      setNotice(result.active_household_id ? "Active household set." : "Cleared active household.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const inviteMutation = useMutation({
    mutationFn: () => createHouseholdInvite(household!.household_id),
    onSuccess: () => setNotice("Invite created."),
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const leaveMutation = useMutation({
    mutationFn: () => leaveHousehold(household!.household_id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["household-bundle"] });
      setNotice("Left household.");
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => removeHouseholdMember(household!.household_id, userId),
    onSuccess: async (_, userId) => {
      await queryClient.invalidateQueries({ queryKey: ["household-bundle"] });
      setNotice(`Removed member.`);
    },
    onError: (err) => setError(err instanceof Error ? err.message : String(err)),
  });

  // Caregiver view queries
  const effectiveSelectedId = selectedMemberUserId || (members.find(m => m.user_id !== user?.user_id)?.user_id ?? user?.user_id ?? null);

  const { data: careProfile } = useQuery({
    queryKey: ["household-care-profile", household?.household_id, effectiveSelectedId],
    queryFn: () => getHouseholdCareMemberProfile(household!.household_id, effectiveSelectedId!),
    enabled: !!household && !!effectiveSelectedId && user?.profile_mode === "caregiver",
  });

  const { data: careSummary } = useQuery({
    queryKey: ["household-care-summary", household?.household_id, effectiveSelectedId],
    queryFn: () => getHouseholdCareMemberDailySummary(household!.household_id, effectiveSelectedId!, new Date().toISOString().slice(0, 10)),
    enabled: !!household && !!effectiveSelectedId && user?.profile_mode === "caregiver",
  });

  const { data: careReminders } = useQuery({
    queryKey: ["household-care-reminders", household?.household_id, effectiveSelectedId],
    queryFn: () => listHouseholdCareMemberReminders(household!.household_id, effectiveSelectedId!),
    enabled: !!household && !!effectiveSelectedId && user?.profile_mode === "caregiver",
  });

  const lastInvite = inviteMutation.data?.invite;

  return (
    <div>
      <PageTitle
        eyebrow="Household"
        title="Shared Wellness Group"
        description="Create a household, invite members, and manage a simple shared group."
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
                  disabled={status !== "authenticated" || createMutation.isPending || Boolean(household)}
                  onClick={() => createMutation.mutate(createName)}
                >
                  <AsyncLabel active={createMutation.isPending} loading="Creating" idle="Create Household" />
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
                  disabled={status !== "authenticated" || joinMutation.isPending || !joinCode.trim() || Boolean(household)}
                  onClick={() => joinMutation.mutate(joinCode.trim())}
                >
                  <AsyncLabel active={joinMutation.isPending} loading="Joining" idle="Join Household" />
                </Button>
              </div>

              {household ? (
                <>
                  <Separator />

                  <div className="space-y-2">
                    <Label htmlFor="household-rename">Rename household</Label>
                    <Input
                      id="household-rename"
                      value={renameValue || (household?.name ?? "")}
                      onChange={(e) => setRenameValue(e.target.value)}
                      placeholder="Household name"
                      disabled={!isOwner}
                    />
                    <Button
                      disabled={renameMutation.isPending || !isOwner || !renameValue.trim() || renameValue.trim() === household.name}
                      onClick={() => renameMutation.mutate(renameValue.trim())}
                    >
                      <AsyncLabel active={renameMutation.isPending} loading="Saving" idle="Rename Household" />
                    </Button>
                  </div>

                  <div className="space-y-2">
                    <Label>Active household (session)</Label>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={setActiveMutation.isPending || activeHouseholdId === household.household_id}
                        onClick={() => setActiveMutation.mutate(household.household_id)}
                      >
                        <AsyncLabel active={setActiveMutation.isPending} loading="Saving" idle="Set Active" />
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={setActiveMutation.isPending || activeHouseholdId == null}
                        onClick={() => setActiveMutation.mutate(null)}
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
                        disabled={inviteMutation.isPending || !isOwner}
                        onClick={() => inviteMutation.mutate()}
                      >
                        <AsyncLabel active={inviteMutation.isPending} loading="Creating" idle="Create Invite Code" />
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
                        disabled={bundleLoading}
                        onClick={() => queryClient.invalidateQueries({ queryKey: ["household-bundle"] })}
                      >
                        <AsyncLabel active={bundleLoading} loading="Refreshing" idle="Refresh Household" />
                      </Button>
                      <Button
                        variant="ghost"
                        disabled={leaveMutation.isPending || !household || isOwner}
                        onClick={() => leaveMutation.mutate()}
                      >
                        <AsyncLabel active={leaveMutation.isPending} loading="Leaving" idle="Leave Household" />
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

        <div className="section-stack">
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
                                disabled={removeMemberMutation.isPending}
                                onClick={() => removeMemberMutation.mutate(member.user_id)}
                              >
                                <AsyncLabel
                                  active={removeMemberMutation.isPending && removeMemberMutation.variables === member.user_id}
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
                      value={effectiveSelectedId ?? ""}
                      onChange={(event) => setSelectedMemberUserId(event.target.value)}
                    >
                      {members.map((member) => (
                        <option key={member.user_id} value={member.user_id}>
                          {member.display_name}
                        </option>
                      ))}
                    </Select>
                    <p className="app-muted text-xs">
                      {effectiveSelectedId === user.user_id
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
