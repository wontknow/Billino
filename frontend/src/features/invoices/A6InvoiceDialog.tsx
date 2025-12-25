"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Invoice } from "@/types/invoice";
import { PDFsService } from "@/services/pdfs";
import { logger } from "@/lib/logger";

interface A6InvoiceDialogProps {
  isOpen: boolean;
  invoices: Invoice[];
  onClose: () => void;
  onSuccess?: () => void;
}

interface AlertState {
  type: "success" | "error";
  message: string;
}

const log = logger.createScoped("📄 A6InvoiceDialog");

export const A6InvoiceDialog: React.FC<A6InvoiceDialogProps> = ({
  isOpen,
  invoices,
  onClose,
  onSuccess,
}) => {
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [alert, setAlert] = useState<AlertState | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setSelectedInvoiceIds([]);
      setAlert(null);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const totalSelected = useMemo(() => selectedInvoiceIds.length, [selectedInvoiceIds]);

  const toggleInvoice = (id: Invoice["id"]) => {
    const numericId = typeof id === "string" ? Number(id) : id;
    if (!Number.isFinite(numericId)) return;
    setSelectedInvoiceIds((prev) =>
      prev.includes(numericId) ? prev.filter((v) => v !== numericId) : [...prev, numericId]
    );
  };

  const handleSubmit = async () => {
    if (selectedInvoiceIds.length === 0) {
      setAlert({ type: "error", message: "Bitte mindestens eine Rechnung wählen." });
      return;
    }

    setIsSubmitting(true);
    setAlert(null);
    try {
      log.debug("Creating A6 PDF", { invoice_ids: selectedInvoiceIds });
      const pdfBlob = await PDFsService.createPdfForA6Invoices(selectedInvoiceIds);

      // Download the PDF
      const url = URL.createObjectURL(pdfBlob.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = pdfBlob.filename;
      link.click();
      URL.revokeObjectURL(url);

      setAlert({ type: "success", message: "A6 PDF wurde erstellt und heruntergeladen." });
      onSuccess?.();
      setTimeout(() => onClose(), 1500);
    } catch (error) {
      log.error("Failed to create A6 PDF", error);
      setAlert({ type: "error", message: "PDF-Erstellung fehlgeschlagen." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>A6 PDF erstellen</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Wählen Sie mehrere Rechnungen aus, um ein kombiniertes PDF im A6-Format zu erstellen
            (ca. 4 Rechnungen pro A4-Seite).
          </p>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Rechnungen auswählen</label>
              <span className="text-xs text-muted-foreground">{totalSelected} ausgewählt</span>
            </div>
            <div className="max-h-64 overflow-auto rounded-md border">
              {invoices.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">Keine Rechnungen vorhanden.</div>
              ) : (
                <ul className="divide-y">
                  {invoices.map((invoice) => {
                    const numericId = typeof invoice.id === "string" ? Number(invoice.id) : invoice.id;
                    const checked = selectedInvoiceIds.includes(Number(numericId));
                    return (
                      <li
                        key={invoice.id}
                        className="flex items-center gap-3 px-4 py-2 hover:bg-muted/50"
                      >
                        <input
                          type="checkbox"
                          className="h-4 w-4"
                          checked={checked}
                          onChange={() => toggleInvoice(invoice.id)}
                        />
                        <div className="flex flex-col text-sm">
                          <span className="font-medium">{invoice.number}</span>
                          <span className="text-muted-foreground">
                            {formatDate(invoice.date)} · {formatAmount(invoice.total_amount)}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>

          {alert && (
            <div
              className={`rounded-md border p-3 text-sm ${
                alert.type === "error"
                  ? "border-destructive/60 text-destructive"
                  : "border-green-500/60 text-green-700"
              }`}
            >
              {alert.message}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Abbrechen
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Wird erstellt…" : "A6 PDF erstellen"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso ?? "—";
    return new Intl.DateTimeFormat("de-DE").format(d);
  } catch {
    return iso ?? "—";
  }
}

function formatAmount(value: unknown) {
  const num = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(num)) return "—";
  return `${num.toFixed(2)} €`;
}

export default A6InvoiceDialog;
