"use client";
import Link from "next/link";

export function Header() {
  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <Link href="/" className="font-semibold">
        Billino
      </Link>
      <div className="text-xs md:text-sm text-muted-foreground">MVP</div>
    </header>
  );
}
