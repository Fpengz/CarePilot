import Link from "next/link";

import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotFoundPage() {
  return (
    <div>
      <PageTitle
        eyebrow="404"
        title="Page Not Found"
        description="The page you requested does not exist or may have moved. Use the navigation above or jump to a known route."
      />
      <Card className="grain-overlay">
        <CardHeader>
          <CardTitle>Try a Known Route</CardTitle>
          <CardDescription>Common destinations for testing API-backed flows.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {[
            ["/login", "Login"],
            ["/dashboard", "Dashboard"],
            ["/meals", "Meals"],
            ["/reports", "Reports"],
            ["/reminders", "Reminders"],
          ].map(([href, label]) => (
            <Button key={href} asChild variant="secondary">
              <Link href={href}>{label}</Link>
            </Button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
