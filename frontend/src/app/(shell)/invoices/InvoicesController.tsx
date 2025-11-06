import { InvoicesService } from "@/services/invoices";
import { InvoicesTable } from "@/features/invoices/InvoicesTable";

export default async function InvoicesController() {
  let error: string | null = null;
  let invoices = [] as Awaited<ReturnType<typeof InvoicesService.list>>;
  try {
    invoices = await InvoicesService.list();
  } catch (err) {
    error = err instanceof Error ? err.message : "Unbekannter Fehler";
  }

  if (error) {
    return (
      <InvoicesTable
        invoices={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Rechnungen gefunden</span>
            <br />
            <span className="text-muted-foreground">failed request</span>
          </>
        }
      />
    );
  }

  return <InvoicesTable invoices={invoices} />;
}
