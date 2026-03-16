import * as React from "react";

export type CompanionIconProps = React.SVGProps<SVGSVGElement>;

export function CompanionIcon({ className, ...props }: CompanionIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      role="img"
      aria-hidden="true"
      className={className}
      fill="none"
      {...props}
    >
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16.6 8.2A5.9 5.9 0 1 0 16.6 15.8" strokeWidth="1.8" />
        <path d="M13.9 9.8A3.6 3.6 0 1 0 13.9 14.2" strokeWidth="1.4" />
      </g>
      <circle cx="16.6" cy="8.2" r="1" fill="currentColor" />
      <circle cx="16.6" cy="15.8" r="1" fill="currentColor" />
      <path d="M9 12h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M12 12h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}
