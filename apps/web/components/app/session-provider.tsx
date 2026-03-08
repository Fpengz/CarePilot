"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { me } from "@/lib/api/auth-client";
import type { SessionUser } from "@/lib/types";

type SessionStatus = "loading" | "authenticated" | "unauthenticated";

interface SessionContextValue {
  status: SessionStatus;
  user: SessionUser | null;
  error: string | null;
  refreshSession: () => Promise<void>;
  hasScope: (scope: string) => boolean;
  isAdmin: boolean;
}

const SessionContext = createContext<SessionContextValue | null>(null);
const PUBLIC_AUTH_ROUTES = new Set(["/login", "/signup"]);

function isUnauthorizedError(error: unknown): boolean {
  return error instanceof Error && error.message.startsWith("API 401:");
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const refreshSession = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setStatus((prev) => (prev === "authenticated" ? prev : "loading"));
    setError(null);

    try {
      const data = await me();
      if (requestId !== requestIdRef.current) return;
      setUser(data.user);
      setStatus("authenticated");
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setUser(null);
      setStatus("unauthenticated");
      if (!isUnauthorizedError(err)) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
  }, []);

  const shouldBootstrapSession = !PUBLIC_AUTH_ROUTES.has(pathname);

  useEffect(() => {
    if (!shouldBootstrapSession) {
      setStatus("unauthenticated");
      setUser(null);
      setError(null);
      return;
    }
    void refreshSession();
  }, [refreshSession, shouldBootstrapSession]);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      user,
      error,
      refreshSession,
      hasScope: (scope: string) => Boolean(user?.scopes.includes(scope)),
      isAdmin: user?.account_role === "admin",
    }),
    [status, user, error, refreshSession],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return value;
}
