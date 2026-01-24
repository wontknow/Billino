import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Billino",
  description: "Release v1.2.0 UI Skeleton (Next.js + shadcn/ui)",
  icons: {
    icon: [
      { url: "/favicon-192.webp", sizes: "192x192", type: "image/webp" },
      { url: "/favicon-512.webp", sizes: "512x512", type: "image/webp" },
    ],
    apple: "/favicon-192.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" suppressHydrationWarning>
      <body className="min-h-dvh bg-background text-foreground">{children}</body>
    </html>
  );
}
