"use client";

import { Loader2, Shield, User } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useSession } from "@/components/app/session-provider";

export function HeaderSessionStatus() {
  const { status, user, error } = useSession();

  if (status === "loading") {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="gap-1.5">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
          Session loading
        </Badge>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">Not signed in</Badge>
        {error ? (
          <Badge variant="outline" className="max-w-[16rem] truncate text-red-700 dark:text-red-200">
            Session error
          </Badge>
        ) : null}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">Session unavailable</Badge>
      </div>
    );
  }

  const RoleIcon = user.account_role === "admin" ? Shield : User;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge className="gap-1.5">
        <RoleIcon className="h-3.5 w-3.5" aria-hidden />
        {user.account_role}
      </Badge>
      <Badge variant="outline">{user.profile_mode}</Badge>
      <Badge variant="outline" className="max-w-[16rem] truncate">
        {user.email}
      </Badge>
    </div>
  );
}
