import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[color:var(--accent)]/12 text-[color:var(--accent)] dark:bg-[color:var(--accent)]/18 dark:text-[#b9efe4]",
        outline:
          "border-[color:var(--border)] bg-white/70 text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)] dark:text-[#cec7ba]",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

function Badge({ className, variant, ...props }: React.ComponentProps<"div"> & VariantProps<typeof badgeVariants>) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
