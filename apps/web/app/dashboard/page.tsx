import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function DashboardPage() {
  return (
    <div>
      <PageTitle
        eyebrow="Overview"
        title="Daily Wellness Workspace"
        description="A responsive shell for meal analysis, reminders, reports, and privileged operations. This page is intentionally lightweight while core backend flows stabilize."
        tags={["account-aware", "profile-mode-aware"]}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Meal Analysis", "Upload and review meals, records, and trace outputs."],
          ["Reminders", "Track generated reminders and meal confirmation rate."],
          ["Reports", "Parse report text and generate grounded recommendations."],
          ["Operations", "Admin-only alerts and workflow timeline inspection."],
        ].map(([title, text]) => (
          <Card key={title} className="grain-overlay">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription>{text}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="mt-4 page-grid">
        <Card>
          <CardHeader>
            <CardTitle>What this shell already validates</CardTitle>
            <CardDescription>Core integration points now align with the refactored account architecture.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Badge>account_role</Badge>
              <Badge variant="outline">scopes</Badge>
              <Badge variant="outline">profile_mode</Badge>
            </div>
            <Separator />
            <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-[color:var(--muted-foreground)]">
              <li>Auth payloads use the new principal contract.</li>
              <li>Privileged routes are gated by scopes, not persona labels.</li>
              <li>Web routes are ready for progressive enhancement without backend churn.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Next UI Iteration Targets</CardTitle>
            <CardDescription>Defer complex product IA until workflow surfaces stabilize.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {[
              "Authenticated sidebar layout and session-aware navigation states",
              "Structured timeline/event viewer for workflow traces",
              "Charts for reminder adherence and meal confirmation trends",
              "Profile-mode-specific content framing for self vs caregiver flows",
            ].map((item) => (
              <div key={item} className="metric-card">
                {item}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
