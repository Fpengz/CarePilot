"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/components/app/session-provider";

export default function RootPage() {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
      return;
    }
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [router, status]);

  return (
    <div className="app-panel flex min-h-[40vh] items-center justify-center p-6">
      <p className="app-muted text-sm">{status === "loading" ? "Checking session…" : "Redirecting…"}</p>
    </div>
  );
}
