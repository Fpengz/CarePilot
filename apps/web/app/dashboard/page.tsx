import Link from "next/link";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
          ["Meal Analysis", "Upload photos, inspect summaries, and review saved records.", "/meals"],
          ["Reminders", "Generate events and confirm meals with metrics feedback.", "/reminders"],
          ["Reports", "Parse report text and produce recommendation outputs.", "/reports"],
          ["Household", "Create a family-like group and manage invites/members.", "/household"],
        ].map(([title, text, href]) => (
          <Card key={title} className="grain-overlay">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription>{text}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <Button asChild size="sm" variant="secondary">
                <Link href={String(href)}>Open</Link>
              </Button>
            </CardContent>
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
              <li>Household flows are now available for create/invite/join/member management.</li>
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
              "Suggestions unified flow (report parse + recommendation in one action)",
              "Household-aware data views for meals/reminders/suggestions",
              "Structured workflow/alert timeline viewers",
              "Charts for adherence and meal confirmation trends",
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
