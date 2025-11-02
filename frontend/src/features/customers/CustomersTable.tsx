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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Customer } from "@/types/customer";
import type React from "react";

type Props = {
  customers: Customer[];
  emptyMessage?: React.ReactNode;
};

export function CustomersTable({ customers, emptyMessage }: Props) {
  const hasData = customers.length > 0;
  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader>
        <CardTitle>Kunden</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        {/* Scrollable area grows with the card while keeping header visible */}
        <div className="h-full overflow-auto">
          <Table>
            <TableCaption>
              {hasData ? `${customers.length} Kunde(n)` : (emptyMessage ?? "Keine Kunden gefunden")}
            </TableCaption>
            <TableHeader className="sticky top-0 z-10 bg-background shadow-sm">
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Adresse</TableHead>
                <TableHead>Stadt</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {customers.map((c) => (
                <TableRow key={c.id}>
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
