"use client";

import React from "react";
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
import type { SummaryInvoiceCompact } from "@/types/summaryInvoices";

interface SummaryInvoicesTableProps {
  summaryInvoices: SummaryInvoiceCompact[];
  onSummarySelect?: (summaryInvoiceId: number) => void;
  onRefresh?: () => void | Promise<void>;
  onCreateSummaryInvoice?: () => void;
  isRefreshing?: boolean;
  emptyMessage?: React.ReactNode;
}

export const SummaryInvoicesTable: React.FC<SummaryInvoicesTableProps> = ({
  summaryInvoices,
  onSummarySelect,
  onRefresh,
  onCreateSummaryInvoice,
  isRefreshing,
  emptyMessage,
}) => {
  const hasData = summaryInvoices.length > 0;
  const isInteractive = typeof onSummarySelect === "function";

  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader>
        <CardTitle>Sammelrechnungen</CardTitle>
        <CardAction className="flex gap-2">
          <Button variant="outline" onClick={onRefresh} disabled={isRefreshing}>
            {isRefreshing ? "Aktualisiert…" : "Aktualisieren"}
          </Button>
          <Button onClick={onCreateSummaryInvoice}>Erstelle Sammelrechnung</Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="h-full overflow-auto">
          <Table>
            <TableCaption>
              {hasData
                ? `${summaryInvoices.length} Sammelrechnung(en)`
                : (emptyMessage ?? "Keine Sammelrechnungen gefunden")}
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-10 bg-background">Bereich</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Datum</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Empfänger</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Netto</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Brutto</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summaryInvoices.map((summary) => {
                const handleActivate = () => onSummarySelect?.(summary.id);
                const handleKeyDown = (event: React.KeyboardEvent<HTMLTableRowElement>) => {
                  if (!isInteractive) return;
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    handleActivate();
                  }
                };

                return (
                  <TableRow
                    key={summary.id}
                    role={isInteractive ? "button" : undefined}
                    tabIndex={isInteractive ? 0 : undefined}
                    onClick={isInteractive ? handleActivate : undefined}
                    onKeyDown={isInteractive ? handleKeyDown : undefined}
                    className={
                      isInteractive
                        ? "cursor-pointer hover:bg-muted/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary/70"
                        : undefined
                    }
                  >
                    <TableCell className="font-medium">{summary.range_text}</TableCell>
                    <TableCell>{formatDate(summary.date)}</TableCell>
                    <TableCell>{summary.recipient_display_name ?? "—"}</TableCell>
                    <TableCell className="text-right">{formatAmount(summary.total_net)}</TableCell>
                    <TableCell className="text-right">{formatAmount(summary.total_gross)}</TableCell>
                  </TableRow>
                );
              })}
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
