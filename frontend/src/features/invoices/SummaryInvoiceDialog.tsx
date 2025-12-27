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
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import type { Invoice } from "@/types/invoice";
import type { Profile } from "@/types/profile";
import type { Customer } from "@/types/customer";
import { SummaryInvoicesService } from "@/services/summaryInvoices";
import { ProfilesService } from "@/services/profiles";
import { CustomersService } from "@/services/customers";
import { logger } from "@/lib/logger";

interface SummaryInvoiceDialogProps {
  isOpen: boolean;
  invoices: Invoice[];
  onClose: () => void;
  onSuccess?: (summaryInvoiceId: number) => void;
}

interface AlertState {
  type: "success" | "error";
  message: string;
}

const log = logger.createScoped("🧾 SummaryInvoiceDialog");

export const SummaryInvoiceDialog: React.FC<SummaryInvoiceDialogProps> = ({
  isOpen,
  invoices,
  onClose,
  onSuccess,
}) => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<number[]>([]);
  const [date, setDate] = useState<string>(() => new Date().toISOString().split("T")[0]);
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // Recipient customer fields
  const [recipientSearchQuery, setRecipientSearchQuery] = useState<string>("");
  const [recipientSuggestions, setRecipientSuggestions] = useState<Customer[]>([]);
  const [selectedRecipientCustomer, setSelectedRecipientCustomer] = useState<Customer | null>(null);
  const [isSearchingRecipient, setIsSearchingRecipient] = useState(false);
  const [showRecipientDropdown, setShowRecipientDropdown] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [alert, setAlert] = useState<AlertState | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const loadProfiles = async () => {
      setIsLoadingProfiles(true);
      try {
        const list = await ProfilesService.list();
        setProfiles(list);
        // preselect first profile if none chosen yet
        if (!selectedProfileId && list.length > 0) {
          setSelectedProfileId(Number(list[0].id));
        }
      } catch (error) {
        log.error("Failed to load profiles", error);
        setAlert({ type: "error", message: "Profile konnten nicht geladen werden." });
      } finally {
        setIsLoadingProfiles(false);
      }
    };
    loadProfiles();
  }, [isOpen, selectedProfileId]);

  // Handle recipient search
  useEffect(() => {
    if (!recipientSearchQuery || recipientSearchQuery.length < 2) {
      setRecipientSuggestions([]);
      return;
    }

    const searchRecipient = async () => {
      setIsSearchingRecipient(true);
      try {
        const results = await CustomersService.search(recipientSearchQuery);
        setRecipientSuggestions(results);
        setShowRecipientDropdown(true);
      } catch (error) {
        log.error("Failed to search customers", error);
        setRecipientSuggestions([]);
      } finally {
        setIsSearchingRecipient(false);
      }
    };

    const debounceTimer = setTimeout(searchRecipient, 300);
    return () => clearTimeout(debounceTimer);
  }, [recipientSearchQuery]);

  useEffect(() => {
    if (!isOpen) {
      // reset when closing
      setSelectedInvoiceIds([]);
      setAlert(null);
      setIsSubmitting(false);
      setRecipientSearchQuery("");
      setSelectedRecipientCustomer(null);
      setRecipientSuggestions([]);
      setShowRecipientDropdown(false);
    }
  }, [isOpen]);

  const filteredInvoices = useMemo(() => {
    if (!dateFrom && !dateTo) return invoices;
    return invoices.filter((invoice) => {
      const invoiceDate = invoice.date;
      if (dateFrom && invoiceDate < dateFrom) return false;
      if (dateTo && invoiceDate > dateTo) return false;
      return true;
    });
  }, [invoices, dateFrom, dateTo]);

  const totalSelected = useMemo(() => selectedInvoiceIds.length, [selectedInvoiceIds]);
  const totalFiltered = useMemo(() => filteredInvoices.length, [filteredInvoices]);

  const toggleInvoice = (id: Invoice["id"]) => {
    const numericId = typeof id === "string" ? Number(id) : id;
    if (!Number.isFinite(numericId)) return;
    setSelectedInvoiceIds((prev) =>
      prev.includes(numericId) ? prev.filter((v) => v !== numericId) : [...prev, numericId]
    );
  };

  const handleSubmit = async () => {
    if (!selectedProfileId) {
      setAlert({ type: "error", message: "Bitte ein Profil auswählen." });
      return;
    }
    if (selectedInvoiceIds.length === 0) {
      setAlert({ type: "error", message: "Bitte mindestens eine Rechnung wählen." });
      return;
    }

    setIsSubmitting(true);
    setAlert(null);
    try {
      log.debug("Creating summary invoice", {
        profile_id: selectedProfileId,
        invoice_ids: selectedInvoiceIds,
        date,
        recipient_customer_id: selectedRecipientCustomer?.id || undefined,
      });
      const summary = await SummaryInvoicesService.createSummaryInvoice({
        profile_id: selectedProfileId,
        invoice_ids: selectedInvoiceIds,
        date,
        recipient_customer_id: selectedRecipientCustomer?.id,
        recipient_name:
          !selectedRecipientCustomer && recipientSearchQuery.trim().length > 0
            ? recipientSearchQuery.trim()
            : undefined,
      });

      // PDF will be generated automatically in the backend in an asynchronous/background process.
      // It may not be immediately available after the summary invoice has been created.
      log.debug(
        "Summary invoice created; PDF generation has been triggered in the backend and will complete asynchronously (it may not be immediately available)."
      );

      setAlert({ type: "success", message: "Sammelrechnung erstellt." });
      onSuccess?.(summary.id);
      onClose();
    } catch (error) {
      log.error("Failed to create summary invoice", error);
      setAlert({ type: "error", message: "Erstellung fehlgeschlagen." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Sammelrechnung erstellen</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Profil</label>
            <Select
              value={selectedProfileId ? String(selectedProfileId) : undefined}
              onValueChange={(value) => setSelectedProfileId(Number(value))}
              disabled={isLoadingProfiles}
            >
              <SelectTrigger className="w-full" />
              <SelectContent>
                {profiles.map((profile) => (
                  <SelectItem key={profile.id} value={String(profile.id)}>
                    {profile.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Datum</label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Filter: Von (optional)</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                placeholder="Startdatum"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Filter: Bis (optional)</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                placeholder="Enddatum"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Empfänger (optional)</label>
            <div className="relative">
              <Input
                type="text"
                placeholder="Kunde suchen oder neue Angabe..."
                value={
                  selectedRecipientCustomer ? selectedRecipientCustomer.name : recipientSearchQuery
                }
                onChange={(e) => {
                  if (selectedRecipientCustomer) {
                    setSelectedRecipientCustomer(null);
                  }
                  setRecipientSearchQuery(e.target.value);
                }}
                onFocus={() => recipientSearchQuery.length >= 2 && setShowRecipientDropdown(true)}
                disabled={isSubmitting}
              />

              {/* Autocomplete dropdown */}
              {showRecipientDropdown && recipientSuggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-md shadow-md">
                  <ul className="max-h-48 overflow-auto">
                    {recipientSuggestions.map((customer) => (
                      <li key={customer.id}>
                        <button
                          type="button"
                          className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 focus:outline-none focus:bg-gray-100"
                          onClick={() => {
                            setSelectedRecipientCustomer(customer);
                            setRecipientSearchQuery("");
                            setShowRecipientDropdown(false);
                            setRecipientSuggestions([]);
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
              {isSearchingRecipient && recipientSearchQuery.length >= 2 && (
                <div className="absolute right-3 top-2.5 text-sm text-muted-foreground">Suche…</div>
              )}

              {/* Selected recipient chip */}
              {selectedRecipientCustomer && (
                <div className="mt-2 flex items-center gap-2 rounded-md bg-gray-100 px-3 py-2 text-sm">
                  <span>
                    {selectedRecipientCustomer.name}
                    {selectedRecipientCustomer.address && ` (${selectedRecipientCustomer.address}`}
                    {selectedRecipientCustomer.city && `, ${selectedRecipientCustomer.city}`}
                    {(selectedRecipientCustomer.address || selectedRecipientCustomer.city) && ")"}
                  </span>
                  <button
                    type="button"
                    className="ml-auto text-gray-500 hover:text-gray-700"
                    onClick={() => {
                      setSelectedRecipientCustomer(null);
                      setRecipientSearchQuery("");
                    }}
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Rechnungen auswählen</label>
              <span className="text-xs text-muted-foreground">
                {totalSelected} ausgewählt · {totalFiltered} gefiltert
              </span>
            </div>
            <div className="max-h-64 overflow-auto rounded-md border">
              {filteredInvoices.length === 0 ? (
                <div className="p-4 text-sm text-muted-foreground">
                  {invoices.length === 0
                    ? "Keine Rechnungen vorhanden."
                    : "Keine Rechnungen im gewählten Zeitraum."}
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
            {isSubmitting ? "Wird erstellt…" : "Sammelrechnung erstellen"}
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

export default SummaryInvoiceDialog;
