import { render, screen } from "@testing-library/react";
import { CustomersTable } from "./CustomersTable";
import type { Customer } from "@/types/customer";

describe("Kundenliste lädt korrekt", () => {
  const sample: Customer[] = [
    { id: 1, name: "Acme GmbH", address: "Hauptstr. 1", city: "Berlin" },
    { id: 2, name: "Muster AG", address: "Bahnhofstr. 2", city: "München" },
  ];

  it("zeigt Spaltenüberschriften und Zeilen bei Daten", () => {
    render(<CustomersTable customers={sample} />);

    // Column headers
    screen.getByRole("columnheader", { name: "Name" });
    screen.getByRole("columnheader", { name: "Adresse" });
    screen.getByRole("columnheader", { name: "Stadt" });

    // Body rows (2)
    // Note: Tables can be tricky, but we can assert the names appear
    screen.getByText("Acme GmbH");
    screen.getByText("Muster AG");

    // Caption shows count
    screen.getByText(/2 Kunde\(n\)/);
  });

  it("zeigt Empty-State ohne Daten", () => {
    render(<CustomersTable customers={[]} />);
    screen.getByText("Keine Kunden gefunden");
  });

  it("zeigt Fehler-Caption bei Fehlerfall (leer + Message)", () => {
    render(
      <CustomersTable customers={[]} emptyMessage="Fehler beim Laden - Keine Kunden gefunden" />
    );
    screen.getByText("Fehler beim Laden - Keine Kunden gefunden");
  });
});
