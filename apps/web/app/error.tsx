"use client";

import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <PageTitle
        eyebrow="Error"
        title="Something Went Wrong"
        description="A route-level error occurred while rendering this page. You can retry, or return to a known route."
      />
      <Card className="grain-overlay">
        <CardHeader>
          <CardTitle className="text-base">Runtime Error</CardTitle>
          <CardDescription>Client route boundary caught an exception.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <pre className="app-code" aria-live="polite">
            {error.message}
          </pre>
          <Button onClick={() => reset()}>Retry</Button>
        </CardContent>
      </Card>
    </div>
  );
}
