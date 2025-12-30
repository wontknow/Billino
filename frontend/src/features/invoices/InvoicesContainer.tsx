"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { PdfViewer } from "@/components/ui/pdf-viewer";
import { PDFsService } from "@/services/pdfs";
import { Invoice } from "@/types/invoice";
import { SummaryInvoiceCompact } from "@/types/summaryInvoices";
import { InvoicesTable } from "./InvoicesTable";
import { SummaryInvoicesTable } from "./SummaryInvoicesTable";
import { SummaryInvoiceDialog } from "./SummaryInvoiceDialog";
import { A6InvoiceDialog } from "./A6InvoiceDialog";
import { useTableState } from "@/hooks/useTableState";
import { fetchTableData } from "@/services/table-api";
import type { ColumnConfig } from "@/components/TableHeader";

type PdfResult = Blob | { blob: Blob; filename?: string };

const normalizePdfResult = (pdf: PdfResult, fallbackFilename: string) => {
  if (pdf instanceof Blob) {
    return { blob: pdf, filename: fallbackFilename };
  }
  return { blob: pdf.blob, filename: pdf.filename ?? fallbackFilename };
};

type TabKey = "invoices" | "summary-invoices";

export interface InvoicesContainerProps {
  invoices: Invoice[];
  summaryInvoices?: SummaryInvoiceCompact[];
  onRefreshInvoices?: () => void | Promise<void>;
  onRefreshSummaryInvoices?: () => void | Promise<void>;
  onOpenCreateSummaryInvoice?: () => void;
  /**
   * Override PDF loader for invoices (DIP). Defaults to PDFsService.getPdfByInvoiceId.
   */
  loadInvoicePdf?: (invoiceId: number) => Promise<PdfResult>;
  /**
   * Override PDF loader for summary invoices (DIP). Defaults to PDFsService.getPdfBySummaryInvoiceId.
   */
  loadSummaryInvoicePdf?: (summaryId: number) => Promise<PdfResult>;
}

export const InvoicesContainer: React.FC<InvoicesContainerProps> = ({
  invoices,
  summaryInvoices = [],
  onRefreshInvoices,
  onRefreshSummaryInvoices,
  onOpenCreateSummaryInvoice,
  loadInvoicePdf,
  loadSummaryInvoicePdf,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>("invoices");
  const [invoicesState, setInvoicesState] = useState<Invoice[]>(invoices);
  const [summaryInvoicesState, setSummaryInvoicesState] =
    useState<SummaryInvoiceCompact[]>(summaryInvoices);
  const [isPdfOpen, setIsPdfOpen] = useState(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfFilename, setPdfFilename] = useState("document.pdf");
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshingInvoices, setIsRefreshingInvoices] = useState(false);
  const [isRefreshingSummary, setIsRefreshingSummary] = useState(false);
  const [isSummaryDialogOpen, setIsSummaryDialogOpen] = useState(false);
  const [isA6DialogOpen, setIsA6DialogOpen] = useState(false);

  // URL-synced state for invoices and summary invoices independently
  const {
    state: invState,
    updateFilters: updateInvFilters,
    updateSort: updateInvSort,
  } = useTableState(10, "inv_");
  const {
    state: sumState,
    updateFilters: updateSumFilters,
    updateSort: updateSumSort,
  } = useTableState(10, "sum_");

  const invoiceColumns: ColumnConfig[] = useMemo(
    () => [
      { id: "number", label: "Nummer", sortable: true, filterable: true, filterType: "text" },
      { id: "date", label: "Datum", sortable: true, filterable: true, filterType: "date" },
      {
        id: "customer_name",
        label: "Empfänger",
        sortable: true,
        filterable: true,
        filterType: "text",
      },
      { id: "profile_name", label: "Profil", sortable: true, filterable: true, filterType: "text" },
      { id: "total_net", label: "Netto", sortable: false, filterable: false },
      { id: "total_gross", label: "Brutto", sortable: false, filterable: false },
    ],
    []
  );

  const summaryColumns: ColumnConfig[] = useMemo(
    () => [
      { id: "range_text", label: "Bereich", sortable: true, filterable: true, filterType: "text" },
      { id: "date", label: "Datum", sortable: true, filterable: true, filterType: "date" },
      {
        id: "recipient_display_name",
        label: "Empfänger",
        sortable: true,
        filterable: true,
        filterType: "text",
      },
      { id: "profile_name", label: "Profil", sortable: true, filterable: true, filterType: "text" },
      { id: "total_net", label: "Netto", sortable: false, filterable: false },
      { id: "total_gross", label: "Brutto", sortable: false, filterable: false },
    ],
    []
  );

  const defaultInvoicePdfLoader = useCallback(
    (invoiceId: number) => PDFsService.getPdfByInvoiceIdWithFallback(invoiceId),
    []
  );

  const defaultSummaryPdfLoader = useCallback(
    (summaryId: number) => PDFsService.getPdfBySummaryInvoiceIdWithFallback(summaryId),
    []
  );

  const tabs = useMemo(
    () => [
      { key: "invoices" as const, label: "Rechnungen" },
      { key: "summary-invoices" as const, label: "Sammelrechnungen" },
    ],
    []
  );

  const handleClosePdf = () => {
    setIsPdfOpen(false);
    setPdfBlob(null);
  };

  // Fetch invoices based on URL state (only when tab is active)
  useEffect(() => {
    if (activeTab !== "invoices") return;
    let mounted = true;
    (async () => {
      const resp = await fetchTableData<Invoice>("/invoices/", invState);
      if (mounted) setInvoicesState(resp.items);
    })();
    return () => {
      mounted = false;
    };
  }, [invState, activeTab]);

  // Fetch summary invoices based on URL state (only when tab is active)
  useEffect(() => {
    if (activeTab !== "summary-invoices") return;
    let mounted = true;
    (async () => {
      const resp = await fetchTableData<SummaryInvoiceCompact>("/summary-invoices/", sumState);
      if (mounted) setSummaryInvoicesState(resp.items);
    })();
    return () => {
      mounted = false;
    };
  }, [sumState, activeTab]);

  const handleOpenInvoicePdf = useCallback(
    async (invoiceId: Invoice["id"]) => {
      const parsedId = typeof invoiceId === "string" ? Number(invoiceId) : invoiceId;
      if (!Number.isFinite(parsedId)) return;
      setErrorMessage(null);
      setIsPdfLoading(true);
      try {
        const loader = loadInvoicePdf ?? defaultInvoicePdfLoader;
        const pdf = await loader(parsedId);
        const normalized = normalizePdfResult(pdf, `invoice-${parsedId}.pdf`);
        setPdfBlob(normalized.blob);
        setPdfFilename(normalized.filename);
        setIsPdfOpen(true);
      } catch {
        setErrorMessage("PDF konnte nicht geladen werden (ggf. noch nicht erzeugt).");
      } finally {
        setIsPdfLoading(false);
      }
    },
    [loadInvoicePdf, defaultInvoicePdfLoader]
  );

  const handleOpenSummaryPdf = useCallback(
    async (summaryId: number) => {
      setIsPdfLoading(true);
      try {
        const loader = loadSummaryInvoicePdf ?? defaultSummaryPdfLoader;
        const pdf = await loader(summaryId);
        const normalized = normalizePdfResult(pdf, `summary-invoice-${summaryId}.pdf`);
        setPdfBlob(normalized.blob);
        setPdfFilename(normalized.filename);
        setIsPdfOpen(true);
      } catch {
        setErrorMessage("Sammelrechnungs-PDF konnte nicht geladen werden.");
      } finally {
        setIsPdfLoading(false);
      }
    },
    [loadSummaryInvoicePdf, defaultSummaryPdfLoader]
  );

  const handleRefreshInvoices = useCallback(async () => {
    setIsRefreshingInvoices(true);
    try {
      if (onRefreshInvoices) await onRefreshInvoices();
      const resp = await fetchTableData<Invoice>("/invoices/", invState);
      setInvoicesState(resp.items);
    } finally {
      setIsRefreshingInvoices(false);
    }
  }, [onRefreshInvoices, invState]);

  const handleRefreshSummary = useCallback(async () => {
    setIsRefreshingSummary(true);
    try {
      if (onRefreshSummaryInvoices) await onRefreshSummaryInvoices();
      const resp = await fetchTableData<SummaryInvoiceCompact>("/summary-invoices/", sumState);
      setSummaryInvoicesState(resp.items);
    } finally {
      setIsRefreshingSummary(false);
    }
  }, [onRefreshSummaryInvoices, sumState]);

  const handleOpenSummaryDialog = () => {
    onOpenCreateSummaryInvoice?.();
    setActiveTab("summary-invoices");
    setIsSummaryDialogOpen(true);
  };

  const handleSummaryCreated = async () => {
    await handleRefreshSummary();
    setIsSummaryDialogOpen(false);
  };

  const handleOpenA6Dialog = () => {
    setIsA6DialogOpen(true);
  };

  return (
    <div className="flex flex-col gap-4">
      {errorMessage && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-4 py-2 text-sm text-destructive">
          {errorMessage}
        </div>
      )}

      <div className="flex gap-2 rounded-lg border p-1 bg-gray-50 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-sm font-medium rounded-md transition ${
              activeTab === tab.key
                ? "bg-white shadow-sm text-gray-900"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "invoices" ? (
        <InvoicesTable
          invoices={invoicesState}
          onInvoiceSelect={handleOpenInvoicePdf}
          onRefresh={handleRefreshInvoices}
          onCreateA6Pdf={handleOpenA6Dialog}
          isRefreshing={isRefreshingInvoices}
          emptyMessage="Keine Rechnungen vorhanden."
          columns={invoiceColumns}
          filters={invState.filters}
          sort={invState.sort}
          onFiltersChange={updateInvFilters}
          onSortChange={updateInvSort}
        />
      ) : (
        <SummaryInvoicesTable
          summaryInvoices={summaryInvoicesState}
          onSummarySelect={handleOpenSummaryPdf}
          onRefresh={handleRefreshSummary}
          onCreateSummaryInvoice={handleOpenSummaryDialog}
          isRefreshing={isRefreshingSummary}
          emptyMessage="Keine Sammelrechnungen vorhanden."
          columns={summaryColumns}
          filters={sumState.filters}
          sort={sumState.sort}
          onFiltersChange={updateSumFilters}
          onSortChange={updateSumSort}
        />
      )}

      <PdfViewer
        isOpen={isPdfOpen}
        blob={pdfBlob}
        filename={pdfFilename}
        isLoading={isPdfLoading}
        onClose={handleClosePdf}
      />

      <SummaryInvoiceDialog
        isOpen={isSummaryDialogOpen}
        invoices={invoicesState}
        onClose={() => setIsSummaryDialogOpen(false)}
        onSuccess={handleSummaryCreated}
      />

      <A6InvoiceDialog
        isOpen={isA6DialogOpen}
        invoices={invoicesState}
        onClose={() => setIsA6DialogOpen(false)}
      />
    </div>
  );
};

export default InvoicesContainer;
