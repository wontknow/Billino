import { InvoicesService } from "@/services/invoices";
import { SummaryInvoicesService } from "@/services/summaryInvoices";
import { InvoicesContainer } from "@/features/invoices/InvoicesContainer";
import type { Invoice } from "@/types/invoice";
import type { SummaryInvoiceCompact } from "@/types/summaryInvoices";

export default async function InvoicesController() {
  let invoices: Invoice[] = [];
  let summaryInvoices: SummaryInvoiceCompact[] = [];

  try {
    invoices = await InvoicesService.list();
  } catch {
    // fall back to empty list; container shows empty state
  }

  try {
    summaryInvoices = await SummaryInvoicesService.getSummaryInvoiceList();
  } catch {
    // optional: ignore and keep empty list
  }

  return <InvoicesContainer invoices={invoices} summaryInvoices={summaryInvoices} />;
}
