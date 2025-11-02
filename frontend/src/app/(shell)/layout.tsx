import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh grid-rows-[auto_1fr]">
      <Header />
      <div className="grid grid-cols-[240px_1fr] md:grid-cols-[280px_1fr]">
        <Sidebar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
