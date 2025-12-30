"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DateRangePicker } from "@/components/ui/date-picker";
import type { Invoice } from "@/types/invoice";
import type { Customer } from "@/types/customer";
import { PDFsService } from "@/services/pdfs";
import { CustomersService } from "@/services/customers";
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

  // Filter states
  const [invoiceNumberFilter, setInvoiceNumberFilter] = useState("");
  const [dateFromFilter, setDateFromFilter] = useState("");
  const [dateToFilter, setDateToFilter] = useState("");
  const [customerSearchQuery, setCustomerSearchQuery] = useState("");
  const [customerSuggestions, setCustomerSuggestions] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [isSearchingCustomer, setIsSearchingCustomer] = useState(false);
  const [showCustomerDropdown, setShowCustomerDropdown] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setSelectedInvoiceIds([]);
      setAlert(null);
      setIsSubmitting(false);
      setInvoiceNumberFilter("");
      setDateFromFilter("");
      setDateToFilter("");
      setCustomerSearchQuery("");
      setSelectedCustomer(null);
      setCustomerSuggestions([]);
      setShowCustomerDropdown(false);
    }
  }, [isOpen]);

  // Handle customer search
  useEffect(() => {
    if (!customerSearchQuery || customerSearchQuery.length < 2) {
      setCustomerSuggestions([]);
      return;
    }

    const searchCustomer = async () => {
      setIsSearchingCustomer(true);
      try {
        const results = await CustomersService.search(customerSearchQuery);
        setCustomerSuggestions(results);
        setShowCustomerDropdown(true);
      } catch (error) {
        log.error("Failed to search customers", error);
        setCustomerSuggestions([]);
      } finally {
        setIsSearchingCustomer(false);
      }
    };

    const debounceTimer = setTimeout(searchCustomer, 300);
    return () => clearTimeout(debounceTimer);
  }, [customerSearchQuery]);

  const totalSelected = useMemo(() => selectedInvoiceIds.length, [selectedInvoiceIds]);

  const filteredInvoices = useMemo(() => {
    return invoices.filter((invoice) => {
      // Filter by invoice number
      if (invoiceNumberFilter && !invoice.number.includes(invoiceNumberFilter)) {
        return false;
      }

      // Filter by date range
      if (dateFromFilter && invoice.date < dateFromFilter) return false;
      if (dateToFilter && invoice.date > dateToFilter) return false;

      // Filter by customer
      if (selectedCustomer && invoice.customer_id !== selectedCustomer.id) {
        return false;
      }

      return true;
    });
  }, [invoices, invoiceNumberFilter, dateFromFilter, dateToFilter, selectedCustomer]);

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

          {/* Filter section */}
          <div className="grid grid-cols-1 gap-4 rounded-md border p-4 bg-muted/30">
            <div className="space-y-2">
              <label className="text-sm font-medium">Nach Rechnungsnummer filtern</label>
              <Input
                type="text"
                placeholder="z.B. 25 | 001"
                value={invoiceNumberFilter}
                onChange={(e) => setInvoiceNumberFilter(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Nach Datum filtern</label>
              <DateRangePicker
                valueFrom={dateFromFilter}
                valueTo={dateToFilter}
                onValueFromChange={setDateFromFilter}
                onValueToChange={setDateToFilter}
                placeholder="Datum auswählen..."
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Nach Kunde filtern</label>
              <div className="relative">
                <Input
                  type="text"
                  placeholder="Kunde suchen..."
                  value={selectedCustomer ? selectedCustomer.name : customerSearchQuery}
                  onChange={(e) => {
                    if (selectedCustomer) {
                      setSelectedCustomer(null);
                    }
                    setCustomerSearchQuery(e.target.value);
                  }}
                  onFocus={() => customerSearchQuery.length >= 2 && setShowCustomerDropdown(true)}
                  disabled={isSubmitting}
                  role="combobox"
                  aria-expanded={showCustomerDropdown}
                  aria-controls="customer-listbox"
                  aria-autocomplete="list"
                />

                {/* Autocomplete dropdown */}
                {showCustomerDropdown && customerSuggestions.length > 0 && (
                  <div
                    id="customer-listbox"
                    className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-md"
                  >
                    <ul className="max-h-48 overflow-auto" role="listbox">
                      {customerSuggestions.map((customer) => (
                        <li
                          key={customer.id}
                          role="option"
                          aria-selected={
                            selectedCustomer ? selectedCustomer.id === customer.id : undefined
                          }
                        >
                          <button
                            type="button"
                            className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 focus:outline-none focus:bg-gray-100"
                            onClick={() => {
                              setSelectedCustomer(customer);
                              setCustomerSearchQuery("");
                              setShowCustomerDropdown(false);
                              setCustomerSuggestions([]);
                            }}
                          >
                            <div className="font-medium">{customer.name}</div>
                            {(customer.address || customer.city) && (
                              <div className="text-xs text-gray-500">
                                {[customer.address, customer.city].filter(Boolean).join(", ")}
                              </div>
                            )}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Loading indicator */}
                {isSearchingCustomer && customerSearchQuery.length >= 2 && (
                  <div className="absolute right-3 top-2.5 text-sm text-muted-foreground">
                    Suche…
                  </div>
                )}

                {/* Selected customer chip */}
                {selectedCustomer && (
                  <div className="mt-2 flex items-center gap-2 rounded-md bg-gray-100 px-3 py-2 text-sm">
                    <span>
                      {selectedCustomer.name}
                      {selectedCustomer.address && ` (${selectedCustomer.address}`}
                      {selectedCustomer.city && `, ${selectedCustomer.city}`}
                      {(selectedCustomer.address || selectedCustomer.city) && ")"}
                    </span>
                    <button
                      type="button"
                      className="ml-auto text-gray-500 hover:text-gray-700"
                      onClick={() => {
                        setSelectedCustomer(null);
                        setCustomerSearchQuery("");
                      }}
                      aria-label="Kundenauswahl entfernen"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Rechnungen auswählen</label>
              <span className="text-xs text-muted-foreground">
                {totalSelected} ausgewählt · {filteredInvoices.length} gefiltert
              </span>
            </div>
            <div className="max-h-64 overflow-auto rounded-md border">
              {filteredInvoices.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">
                  {invoices.length === 0
                    ? "Keine Rechnungen vorhanden."
                    : "Keine Rechnungen mit den angegebenen Filtern gefunden."}
                </div>
              ) : (
                <ul className="divide-y">
                  {filteredInvoices.map((invoice) => {
                    const numericId =
                      typeof invoice.id === "string" ? Number(invoice.id) : invoice.id;
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
                            {invoice.customer_name && ` · ${invoice.customer_name}`}
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
