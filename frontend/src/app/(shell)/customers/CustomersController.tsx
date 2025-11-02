import { CustomersService } from "@/services/customers";
import { CustomersTable } from "@/features/customers/CustomersTable";

export default async function CustomersController() {
  let error: string | null = null;
  let customers = [] as Awaited<ReturnType<typeof CustomersService.list>>;
  try {
    customers = await CustomersService.list();
  } catch (err) {
    error = err instanceof Error ? err.message : "Unbekannter Fehler";
  }

  if (error) {
    // Show table headers with no data and an explicit error-flavored empty message
    return (
      <CustomersTable customers={[]} emptyMessage="Fehler beim Laden - Keine Kunden gefunden" />
    );
  }

  return <CustomersTable customers={customers} />;
}
