"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/chat", label: "💬 Chat" },
  { href: "/medications", label: "💊 Medications" },
  { href: "/dashboard", label: "📊 Dashboard" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 flex items-center gap-2 h-14">
        <span className="font-bold text-brand-700 text-lg mr-4">
          🦁 SEA-LION Health
        </span>
        {LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              pathname.startsWith(href)
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
