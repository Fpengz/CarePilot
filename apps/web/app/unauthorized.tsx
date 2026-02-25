import { PageTitle } from "@/components/app/page-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function UnauthorizedPage() {
  return (
    <div>
      <PageTitle eyebrow="Auth" title="Unauthorized" description="Please sign in to continue to this page." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Authentication Required</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-[color:var(--muted-foreground)]">
          Your session is missing or expired. Return to login and authenticate again.
        </CardContent>
      </Card>
    </div>
  );
}
