"use client";

import React from "react";
import {
  Table,
  TableHeader as ShadTableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { SummaryInvoiceCompact } from "@/types/summaryInvoices";
import { TableHeader as AdvancedTableHeader } from "@/components/TableHeader";
import type { ColumnConfig } from "@/components/TableHeader";
import type { ColumnFilter, SortField } from "@/types/table-filters";

interface SummaryInvoicesTableProps {
  summaryInvoices: SummaryInvoiceCompact[];
  onSummarySelect?: (summaryInvoiceId: number) => void;
  onRefresh?: () => void | Promise<void>;
  onCreateSummaryInvoice?: () => void;
  isRefreshing?: boolean;
  emptyMessage?: React.ReactNode;
  columns?: ColumnConfig[];
  filters?: ColumnFilter[];
  sort?: SortField[];
  onFiltersChange?: (filters: ColumnFilter[]) => void;
  onSortChange?: (sort: SortField[]) => void;
}

export const SummaryInvoicesTable: React.FC<SummaryInvoicesTableProps> = ({
  summaryInvoices,
  onSummarySelect,
  onRefresh,
  onCreateSummaryInvoice,
  isRefreshing,
  emptyMessage,
  columns,
  filters,
  sort,
  onFiltersChange,
  onSortChange,
}) => {
  const hasData = summaryInvoices.length > 0;
  const isInteractive = typeof onSummarySelect === "function";

  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader>
        <CardTitle className="text-2xl">Sammelrechnungen</CardTitle>
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
            {columns && sort && filters && onSortChange && onFiltersChange ? (
              <AdvancedTableHeader
                columns={columns}
                sort={sort}
                filters={filters}
                onSortChange={onSortChange}
                onFilterChange={onFiltersChange}
              />
            ) : (
              <ShadTableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-10 bg-background">Bereich</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-background">Datum</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-background">Empfänger</TableHead>
                  <TableHead className="sticky top-0 z-10 bg-background text-right min-w-[5.5rem] px-2 pr-5">
                    Netto
                  </TableHead>
                  <TableHead className="sticky top-0 z-10 bg-background text-right min-w-[5.5rem] px-2 pl-3">
                    Brutto
                  </TableHead>
                </TableRow>
              </ShadTableHeader>
            )}
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
                    <TableCell className="text-right tabular-nums min-w-[5.5rem] px-2 pr-5">
                      {formatAmount(summary.total_net)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums min-w-[5.5rem] px-2 pl-3">
                      {formatAmount(summary.total_gross)}
                    </TableCell>
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
