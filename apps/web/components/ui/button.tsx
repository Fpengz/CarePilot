import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-semibold transition-all outline-none disabled:pointer-events-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-[color:var(--background)] active:translate-y-px",
  {
    variants: {
      variant: {
        default:
          "bg-[color:var(--accent)] text-[color:var(--accent-foreground)] shadow-[0_8px_18px_rgba(16,92,182,0.2)] hover:brightness-105",
        secondary:
          "bg-[color:var(--surface)] text-[color:var(--foreground)] border border-[color:var(--border)] hover:bg-[color:var(--panel-soft)]",
        ghost: "text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-11 px-5 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
