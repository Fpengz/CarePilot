import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ErrorCard({ message, title = "Request Error" }: { message: string; title?: string }) {
  return (
    <Card className="border-red-300/80 bg-red-50/70 dark:border-red-900/70 dark:bg-red-950/25" aria-live="polite">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription className="text-red-900/80 dark:text-red-200">{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}
