import { cn } from "@/lib/utils";

function Separator({ className, ...props }: React.ComponentProps<"div">) {
  return <div aria-hidden className={cn("h-px w-full bg-[color:var(--border)]", className)} {...props} />;
}

export { Separator };
