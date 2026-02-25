import { PageTitle } from "@/components/app/page-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ForbiddenPage() {
  return (
    <div>
      <PageTitle
        eyebrow="Access"
        title="Permission Required"
        description="Your current account permissions do not allow access to this resource. Use an account with the required scopes or switch to the appropriate environment."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Permission Check Failed</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-[color:var(--muted-foreground)]">
          This route is reachable, but the backend authorization policy denied the request.
        </CardContent>
      </Card>
    </div>
  );
}
