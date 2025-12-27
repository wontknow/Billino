"use client";

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Customer } from "@/types/customer";
import type React from "react";

type Props = {
  customers: Customer[];
  emptyMessage?: React.ReactNode;
  onCustomerSelect?: (customerId: number) => void;
  onCreateCustomer?: () => void;
};

export function CustomersTable({
  customers,
  emptyMessage,
  onCustomerSelect,
  onCreateCustomer,
}: Props) {
  const hasData = customers.length > 0;
  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div className="space-y-1">
          <CardTitle>Kunden</CardTitle>
        </div>
        {onCreateCustomer && (
          <CardAction className="flex gap-2">
            <Button onClick={onCreateCustomer}>Neuer Kunde</Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        {/* Scrollable area grows with the card while keeping header visible */}
        <div className="h-full overflow-auto">
          <Table>
            <TableCaption>
              {hasData ? `${customers.length} Kunde(n)` : (emptyMessage ?? "Keine Kunden gefunden")}
            </TableCaption>
            {/* Use sticky on header cells for better cross-browser support */}
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-10 bg-background">Name</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Adresse</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Stadt</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {customers.map((c) => (
                <TableRow
                  key={c.id}
                  onClick={() => onCustomerSelect?.(c.id)}
                  className={onCustomerSelect ? "cursor-pointer hover:bg-muted/50" : undefined}
                  tabIndex={onCustomerSelect ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (onCustomerSelect && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onCustomerSelect(c.id);
                    }
                  }}
                >
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell>{c.address ?? "—"}</TableCell>
                  <TableCell>{c.city ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
