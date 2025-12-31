import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Billino",
  description: "Release v1.2.0 UI Skeleton (Next.js + shadcn/ui)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" suppressHydrationWarning>
      <body className="min-h-dvh bg-background text-foreground">{children}</body>
    </html>
  );
}
