"use client";

import { useEffect, useState, useCallback } from "react";
import { CustomersService } from "@/services/customers";
import { CustomersTable } from "@/features/customers/CustomersTable";
import { CustomerDialog } from "@/features/customers/CustomerDialog";
import type { Customer } from "@/types/customer";

export default function CustomersController() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  const loadCustomers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await CustomersService.list();
      setCustomers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }, []);

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
