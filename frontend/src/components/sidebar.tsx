"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const items = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/customers", label: "Kunden" },
  { href: "/profiles", label: "Profile" },
  { href: "/invoices", label: "Rechnungen" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="border-r bg-muted/20">
      <div className="p-4 font-medium">Navigation</div>
      <nav className="grid gap-1 px-2 pb-4">
        {items.map((it) => {
          const active = pathname?.startsWith(it.href);
          return (
            <Link
              key={it.href}
              href={it.href}
              className={clsx(
                "rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
                active
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {it.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
