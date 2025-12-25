"use client";

import React from "react";
import Link from "next/link";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Invoice } from "@/types/invoice";

interface InvoicesTableProps {
  invoices: Invoice[];
  onInvoiceSelect?: (invoiceId: Invoice["id"]) => void;
  onRefresh?: () => void | Promise<void>;
  onCreateA6Pdf?: () => void;
  isRefreshing?: boolean;
  emptyMessage?: React.ReactNode;
}

export const InvoicesTable: React.FC<InvoicesTableProps> = ({
  invoices,
  emptyMessage,
  onInvoiceSelect,
  onRefresh,
  onCreateA6Pdf,
  isRefreshing,
}) => {
  const hasData = invoices.length > 0;

  const handleRowClick = (id: Invoice["id"]) => {
    if (!onInvoiceSelect) return;
    onInvoiceSelect(id);
  };

  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div className="space-y-1">
          <CardTitle>Rechnungen</CardTitle>
        </div>
        <CardAction className="flex gap-2">
          {onRefresh && (
            <Button variant="outline" onClick={onRefresh} disabled={isRefreshing}>
              {isRefreshing ? "Aktualisiert…" : "Aktualisieren"}
            </Button>
          )}
          {onCreateA6Pdf && (
            <Button variant="outline" onClick={onCreateA6Pdf}>
              A6 PDF
            </Button>
          )}
          <Button asChild>
            <Link href="/invoices/create">Neue Rechnung</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="h-full overflow-auto">
          <Table>
            <TableCaption>
              {hasData ? `${invoices.length} Rechnung(en)` : emptyMessage ?? "Keine Rechnungen gefunden"}
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-10 bg-background">Nummer</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Datum</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Summe</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((inv) => (
                <TableRow
                  key={inv.id}
                  role={onInvoiceSelect ? "button" : undefined}
                  className={onInvoiceSelect ? "cursor-pointer" : undefined}
                  tabIndex={onInvoiceSelect ? 0 : -1}
                  onClick={() => handleRowClick(inv.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleRowClick(inv.id);
                    }
                  }}
                >
                  <TableCell className="font-medium">{inv.number}</TableCell>
                  <TableCell>{formatDate(inv.date)}</TableCell>
                  <TableCell>{formatAmount(inv.total_amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
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
