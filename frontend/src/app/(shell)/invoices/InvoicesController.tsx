import { InvoicesContainer } from "@/features/invoices/InvoicesContainer";
import type { Invoice } from "@/types/invoice";
import type { SummaryInvoiceCompact } from "@/types/summaryInvoices";

export default async function InvoicesController() {
  // Initial render can be empty; client container will fetch with URL state
  const invoices: Invoice[] = [];
  const summaryInvoices: SummaryInvoiceCompact[] = [];
  return <InvoicesContainer invoices={invoices} summaryInvoices={summaryInvoices} />;
}
