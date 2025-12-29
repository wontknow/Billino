"use client";

import { useEffect, useState, useCallback } from "react";
import { CustomersService } from "@/services/customers";
import { CustomersTable } from "@/features/customers/CustomersTable";
import { CustomerDialog } from "@/features/customers/CustomerDialog";
import type { Customer } from "@/types/customer";
import { useTableState } from "@/hooks/useTableState";
import { fetchTableData } from "@/services/table-api";
import type { ColumnConfig } from "@/components/TableHeader";

export default function CustomersController() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  // URL-synchronisierter Tabellenzustand (Filter, Sort, Suche, Pagination)
  const { state, updateFilters, updateSort } = useTableState(10);

  // Spalten-Definitionen für erweiterte Header-/Filter-UI
  const columns: ColumnConfig[] = [
    { id: "name", label: "Name", sortable: true, filterable: true, filterType: "text" },
    { id: "address", label: "Adresse", sortable: true, filterable: true, filterType: "text" },
    { id: "city", label: "Stadt", sortable: true, filterable: true, filterType: "text" },
  ];

  const loadCustomers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      // Hole Daten serverseitig gefiltert/sortiert/paginiert
      const resp = await fetchTableData<Customer>("/customers/", state);
      setCustomers(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }, [state]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  const handleCreateCustomer = () => {
    setSelectedCustomer(null);
    setIsDialogOpen(true);
  };

  const handleEditCustomer = (customerId: number) => {
    const customer = customers.find((c) => c.id === customerId);
    if (customer) {
      setSelectedCustomer(customer);
      setIsDialogOpen(true);
    }
  };

  const handleDialogSuccess = async () => {
    await loadCustomers();
  };

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setSelectedCustomer(null);
  };

  if (loading) {
    return <CustomersTable customers={[]} emptyMessage={<span>Lädt Kunden...</span>} />;
  }

  if (error) {
    return (
      <CustomersTable
        customers={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Kunden gefunden</span>
            <br />
            <span className="text-muted-foreground">failed request</span>
          </>
        }
      />
    );
  }

  return (
    <>
      <CustomersTable
        customers={customers}
        onCustomerSelect={handleEditCustomer}
        onCreateCustomer={handleCreateCustomer}
        // Erweiterte Filter-/Sort-UI
        columns={columns}
        filters={state.filters}
        sort={state.sort}
        onFiltersChange={updateFilters}
        onSortChange={updateSort}
      />
      <CustomerDialog
        isOpen={isDialogOpen}
        customer={selectedCustomer}
        onClose={handleDialogClose}
        onSuccess={handleDialogSuccess}
      />
    </>
  );
}
