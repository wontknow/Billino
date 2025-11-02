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
    // Show table headers with no data and an explicit, multi-line message
    return (
      <CustomersTable
        customers={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Kunden gefunden</span>
            <br />
            <span className="text-muted-foreground">Backend nicht erreichbar</span>
          </>
        }
      />
    );
  }

  return <CustomersTable customers={customers} />;
}
